""" Record some audio """

import wave
import sys

import pyaudio
import time
from math import log10
import audioop
import RPi.GPIO as GPIO

# GPIO CONFIG
# RBPY Channels Start at 1 on left, 2 on right, and are even/odd
GPIO.setmode(GPIO.BOARD)
GPIO.setup([11, 13, 15], GPIO.OUT, initial=GPIO.LOW)

# PYAUDIO SETTINGS (WORKING)
WIDTH = 2
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1 if sys.platform == 'darwin' else 2
RATE = 44100 
RECORD_SECONDS = 5
rms = 1

with wave.open('output.wav', 'wb') as wf:
    p = pyaudio.PyAudio()
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)

    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True)
    stream.start_stream()
    print('Recording...')

    for _ in range(0, RATE // CHUNK * RECORD_SECONDS):
        sample = stream.read(CHUNK)
        wf.writeframes(sample)
        rms = audioop.rms(sample, WIDTH) / 32767
        db = 20*log10(rms)
        if (db > -10):
            GPIO.output(11, GPIO.HIGH)
        else:
            GPIO.output(11, GPIO.LOW)
        print(f"RMS: {rms} DB: {db}")
        #print(sample)

    print('Done')

    stream.close()
    GPIO.cleanup()
    #stream.stop_stream() # use close if blocking ?
    p.terminate()
"""
    for _ in range(0, RATE // CHUNK * RECORD_SECONDS):
        sample = stream.read(CHUNK)
        wf.writeframes(sample)
        print(sample)
    print('Done')
"""
#    stream.close()

"""
    def callback(in_data, frame_count, time_info, status):
        global rms
        rms = audioop.rms(in_data, WIDTH) / 32767
        print(f"RECORDING {in_data}")
        return in_data, pyaudio.paContinue
"""
"""
    while stream.is_active():
        db = 20*log10(rms)
        print(f"RMS: {rms} DB: {db}")
        time.sleep(0.3)
"""
