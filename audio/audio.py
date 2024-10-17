""" Record and play audio with adjustable thresholds using rotary encoders """

import wave
import sys
import pyaudio
import time
from math import log10
import audioop
import RPi.GPIO as GPIO
import threading
import numpy as np
from scipy.fft import fft

# Global configuration for audio analysis
ENABLE_AUDIO_ANALYSIS = True  # Set to False to disable audio analysis

# GPIO Configuration
GPIO.setmode(GPIO.BOARD)

# LED pins for visual feedback
RECORD_LED_PIN = 11
PLAYBACK_LED_PIN = 15
GPIO.setup([RECORD_LED_PIN, PLAYBACK_LED_PIN], GPIO.OUT, initial=GPIO.LOW)

# Button pin for controlling record/playback
CONTROL_BUTTON_PIN = 7
GPIO.setup(CONTROL_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Rotary Encoder Pins
RECORD_CLK = 17
RECORD_DT = 18
PLAYBACK_CLK = 22
PLAYBACK_DT = 23

GPIO.setup([RECORD_CLK, RECORD_DT, PLAYBACK_CLK, PLAYBACK_DT], GPIO.IN, pull_up_down=GPIO.PUD_UP)

# PyAudio Configuration
WIDTH = 2
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1 if sys.platform == 'darwin' else 2
RATE = 44100

# Global state variables
recording = False
playing = False
stop_recording = threading.Event()
stop_playing = threading.Event()

# Threshold values for record and playback
record_threshold = -30
playback_threshold = -30
record_counter = 0
playback_counter = 0

# Add this to your global variables
VOLUME_BOOST = 5  # Adjust this value to increase or decrease the volume boost

# Define LED pins for frequency bands (adjust as needed)
FREQ_LED_PINS = [29, 31, 33, 35, 37]  # Example pins for 5 frequency bands
GPIO.setup(FREQ_LED_PINS, GPIO.OUT, initial=GPIO.LOW)

# Define frequency bands and thresholds
FREQ_BANDS = [
    (20, 200),    # Low
    (200, 800),   # Low-Mid
    (800, 2000),  # Mid
    (2000, 8000), # High-Mid
    (8000, 20000) # High
]
FREQ_THRESHOLDS = [-30, -30, -30, -30, -30]  # Adjust these thresholds as needed

def record_encoder_callback(channel):
    """Callback function for record threshold rotary encoder"""
    global record_counter, record_threshold
    clk_state = GPIO.input(RECORD_CLK)
    dt_state = GPIO.input(RECORD_DT)
    if clk_state != dt_state:
        record_counter += 1
        record_threshold = min(-10, record_threshold + 1)
    else:
        record_counter -= 1
        record_threshold = max(-50, record_threshold - 1)
    print(f"Record Threshold: {record_threshold} dB")

def playback_encoder_callback(channel):
    """Callback function for playback threshold rotary encoder"""
    global playback_counter, playback_threshold
    clk_state = GPIO.input(PLAYBACK_CLK)
    dt_state = GPIO.input(PLAYBACK_DT)
    if clk_state != dt_state:
        playback_counter += 1
        playback_threshold = min(-10, playback_threshold + 1)
    else:
        playback_counter -= 1
        playback_threshold = max(-50, playback_threshold - 1)
    print(f"Playback Threshold: {playback_threshold} dB")

def record_audio():
    """Function to record audio and save it to a file"""
    global recording
    with wave.open('output.wav', 'wb') as wf:
        p = pyaudio.PyAudio()
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)

        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        print('Recording...')

        while not stop_recording.is_set():
            sample = stream.read(CHUNK)
            
            # Apply volume boost using audioop.mul
            boosted_sample = audioop.mul(sample, WIDTH, VOLUME_BOOST)
            
            wf.writeframes(boosted_sample)
            rms = audioop.rms(boosted_sample, WIDTH) / 32767
            db = 20 * log10(rms)
            GPIO.output(RECORD_LED_PIN, GPIO.HIGH if db > record_threshold else GPIO.LOW)
            print(f"Recording - RMS: {rms:.4f} DB: {db:.2f} Threshold: {record_threshold:.2f}")

        print('Recording stopped')
        stream.stop_stream()
        stream.close()
        p.terminate()
    recording = False

def analyze_chunk(data, sample_rate):
    """Analyze frequency content of a single chunk of audio data"""
    if not ENABLE_AUDIO_ANALYSIS:
        return []

    fft_result = fft(data)
    frequencies = np.fft.fftfreq(len(fft_result), 1/sample_rate)
    magnitudes = np.abs(fft_result)
    
    band_magnitudes = []
    for low, high in FREQ_BANDS:
        band_freq_indices = np.where((frequencies >= low) & (frequencies < high))
        band_magnitude = np.mean(magnitudes[band_freq_indices])
        band_magnitudes.append(band_magnitude)
    
    return band_magnitudes

def play_audio():
    """Function to play back the recorded audio file and analyze frequencies"""
    global playing
    with wave.open('output.wav', 'rb') as wf:
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)
        
        print('Playing...')
        data = wf.readframes(CHUNK)
        while data and not stop_playing.is_set():
            stream.write(data)
            
            # Convert bytes to numpy array
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Analyze frequencies
            band_magnitudes = analyze_chunk(audio_data, wf.getframerate())
            
            # Drive LEDs based on frequency content
            for i, (magnitude, threshold, led_pin) in enumerate(zip(band_magnitudes, FREQ_THRESHOLDS, FREQ_LED_PINS)):
                db = 20 * log10(magnitude / 32767) if magnitude > 0 else -100
                GPIO.output(led_pin, GPIO.HIGH if db > threshold else GPIO.LOW)
                print(f"Band {i+1}: {db:.2f} dB")
            
            # Original volume-based LED logic
            rms = audioop.rms(data, WIDTH) / 32767
            db = 20 * log10(rms)
            GPIO.output(PLAYBACK_LED_PIN, GPIO.HIGH if db > playback_threshold else GPIO.LOW)
            print(f"Playback - RMS: {rms:.4f} DB: {db:.2f} Threshold: {playback_threshold:.2f}")
            
            data = wf.readframes(CHUNK)

        print('Playback stopped')
        stream.stop_stream()
        stream.close()
        p.terminate()
    playing = False

def button_callback(channel):
    """Callback function for the control button"""
    global recording, playing
    if not recording and not playing:
        # Start recording
        recording = True
        stop_recording.clear()
        threading.Thread(target=record_audio).start()
    elif recording:
        # Stop recording
        stop_recording.set()
    elif not playing:
        # Start playback
        playing = True
        stop_playing.clear()
        threading.Thread(target=play_audio).start()
    else:
        # Stop playback
        stop_playing.set()

# Set up GPIO event detection
GPIO.add_event_detect(CONTROL_BUTTON_PIN, GPIO.FALLING, callback=button_callback, bouncetime=300)
GPIO.add_event_detect(RECORD_CLK, GPIO.BOTH, callback=record_encoder_callback, bouncetime=50)
GPIO.add_event_detect(PLAYBACK_CLK, GPIO.BOTH, callback=playback_encoder_callback, bouncetime=50)

# Main program loop
try:
    print("Audio Recorder and Player")
    print("-------------------------")
    print("Press the button to start/stop recording or playback")
    print(f"Initial Record Threshold: {record_threshold} dB")
    print(f"Initial Playback Threshold: {playback_threshold} dB")
    print("Use rotary encoders to adjust thresholds")
    print(f"Audio Analysis: {'Enabled' if ENABLE_AUDIO_ANALYSIS else 'Disabled'}")
    print("Press Ctrl+C to exit")
    
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nProgram terminated by user")
finally:
    GPIO.cleanup()
