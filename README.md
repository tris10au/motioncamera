# motioncamera
Motion-detection camera with automatic recording, temperature monitoring and simple web UI. Originally designed for monitoring pets while away, this sends push notifications using [Pushover](https://pushover.net)

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
python3 main.py
```

Or you can use tmux (see `start-server.sh`).

As this uses camera processing, you will likely need a fan which is what `enhanced-fanctl` was originally written for.

## Acknowledgements
https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
