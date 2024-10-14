Set up RBPi with Hotspot for internet connectivity
Follow https://github.com/opencardev/snd-i2s_rpi to set up drivers and kernel

run sudo modprobe snd-i2s_rpi
after reboot

Follow https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test for rest of install
Follow https://www.reddit.com/r/linuxquestions/comments/9ok3jf/increase_alsa_recording_volume_to_more_than_100/ for sound boosting
PyAudio: https://people.csail.mit.edu/hubert/pyaudio/
make sure you install other deps (will throw errors otherwise)
Create venv env
