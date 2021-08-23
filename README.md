# motioncamera
Motion-detection camera with automatic recording, temperature monitoring, light controls and simple web UI. Originally designed for monitoring pets while away, this sends push notifications using [Pushover](https://pushover.net)

## Equipment
This was written/cobbled together to quickly fill a specific need: monitoring and managing a pet while away. It is designed to use:L
 - Raspberry Pi as the server
 - USB webcam connected to the RPi for the camera
 - A Xiamo LYWSD03MMC temperature sensor for environment (temperature and humidity) monitoring
 - An LED strip using MagicHue that tracks sunrise and sunset. Unfortunately the LED strip was very unreliable, so I added a Meross smart power plug to it so I could automatically reboot it whenenver the LED strip stopped responding (~once per day).

## Setup
Edit the configuration values in `camera.py` and `climate.py`, including the base URL and Pushover API tokens.

To use, install:
 - `opencv-python`
 - `imutils`
 - `python-requests`
 - `lywsd03mmc`
 - `Pillow`
 - `flask`

## Usage
Using systemd, start the following concurrently:
```
python3 climate.py &
python3 lighting.py &
python3 main.py
```

Or you can use tmux (see `start-server.sh`).

As this uses camera processing, you will likely need a fan which is what `enhanced-fanctl` was originally written for.

## Acknowledgements
https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
