import cv2
import imutils
import os
import io
from datetime import datetime, timedelta
import time
import requests
import traceback
import queue
import threading


# CONFIG
DEBUG = False  # Whether to save frames for debugging purposes
RECORD_MOTION = True  # Whether to record when motion is detected
NOTIFY_MOTION = True  # Whether to notify when motion is detected


CAMERA_RESOLUTION = (1920, 1080)  # Resolution of the camera
RECORD_TIME = 2 * 60  # Time in seconds to record after motion is detected
SAVE_FOLDER = "photos"  # Folder to save recording photos to

NOTIFY_MAX_FREQ = 30 * 60 # Minimum time between detections to notify (in secs)
NOTIFY_APP_TOKEN = "YOUR_APP_TOKEN_HERE"  # Pushover application token
NOTIFY_USER_TOKEN = "YOUR_USER_TOKEN_HERE"  # Pushover user or group token
BASE_URL = "http://YOUR_SERVER_HERE.:8080/#"  # The URL to use in notifications


CAMERA = None
BUFFER = None
LAST_SAVE = None
LAST_NOTIFY = None
RECORD_MODE = False
RECORD_START = None

BUFFER_SAVE = None
IMAGE = None
LAST_FRAME = None

RECORD_MOTION = True
NOTIFY_MOTION = True
LAST_NOTIFY = None

class LatestFrame(object):
    camera = None

    def __init__(self, name):
        self.lock = threading.Lock()
        self.data = (False, None)
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    def get_camera(self):
        try:
            if self.camera is None:
                self.camera = cv2.VideoCapture(0)
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_RESOLUTION[0])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_RESOLUTION[1 ])
                self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return self.camera.read()
        except Exception as e:
            print("CAMERA ERROR")
            traceback.print_exc()
            return (False, None)

    # read frames as soon as they are available, keeping only most recent one
    def _reader(self):
        while True:
            ret, frame = self.get_camera()
            if not ret or frame is None or frame.shape[0] == 0:
                print("Camera sleep")
                time.sleep(0.2)
                break
            with self.lock:
                self.data = (datetime.now(), frame)


    def read(self):
        with self.lock:
            return self.data


def get_frame():
    global CAMERA

    if CAMERA is None:
        CAMERA = LatestFrame(0)

    return CAMERA.read()


def capture_buffer():
    global BUFFER, BUFFER_SAVE, IMAGE

    status, frame = get_frame()
    if status:
        frame = cv2.resize(frame, (frame.shape[1] // 2, frame.shape[0] // 2))
        status2, jpg = cv2.imencode(".jpg", frame)
        BUFFER = frame
        BUFFER_SAVE = status
        if status2:
            IMAGE = jpg
        return frame
    return None


def capture_image():
    global IMAGE, BUFFER_SAVE, RECORD_MODE

    capture_buffer()

    return BUFFER_SAVE, io.BytesIO(IMAGE), RECORD_MODE


def print_frame(name, frame):
    if frame is None:
        print(name, "=", frame)
        return

    print(name, "=", frame.shape[1], frame.shape[0])


def run_task():
    global LAST_FRAME, LAST_SAVE, LAST_NOTIFY, SAVE_FOLDER, RECORD_MODE
    global RECORD_START, IMAGE, BUFFER, BUFFER_SAVE, RECORD_MOTION, NOTIFY_MOTION

    DEBUG = True

    if not os.path.exists(SAVE_FOLDER):
        os.makedirs(SAVE_FOLDER)

    if not RECORD_MOTION:
        return

    last_frame = LAST_FRAME
    frame = capture_buffer()
    if frame is None:
        print("ERROR: Could not capture frame")
        return

    if RECORD_MODE:
        d = datetime.now()
        with open(os.path.join(SAVE_FOLDER, d.strftime("%Y-%m-%d_%H-%M-%S") + ".jpg"), "wb") as f:
            f.write(IMAGE)
        print("Recording in progress")

        if RECORD_START is None:
            RECORD_START = datetime.now()

        if (datetime.now() - RECORD_START).total_seconds() >= RECORD_TIME:
            print("Recording ending")
            RECORD_MODE = False
            RECORD_START = None
            last_frame = None

    
    frame = cv2.resize(frame, (frame.shape[1] // 3, frame.shape[0] // 3))
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame_gray = cv2.GaussianBlur(frame_gray, (21, 21), 0)

    if DEBUG:
        img = cv2.imwrite("grayframe.jpg", frame_gray)
    
    if last_frame is None or RECORD_MODE:
        print("Skipping motion check as recording/no frame")
        LAST_FRAME = frame_gray
        return

    delta = None
    try:
        delta = cv2.absdiff(last_frame, frame_gray)
    except Exception as e:
        print_frame("last_frame", last_frame)
        print_frame("frame_gray", frame_gray)
        raise e

    thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = imutils.grab_contours(contours)

    valid = False
    for contour in contours:
        if cv2.contourArea(contour) > 128:
            print("Found contour area =", cv2.contourArea(contour))
            valid = True

    if valid:
        print("Found motion! Starting recording")
        fdate = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") 
        with open(os.path.join(SAVE_FOLDER, fdate + ".jpg"), "wb") as f:
            f.write(IMAGE)
        RECORD_MODE = True

        if NOTIFY_MOTION and (LAST_NOTIFY is None or (datetime.now() - LAST_NOTIFY).total_seconds() > NOTIFY_MAX_FREQ):
            print("Sending notification...")
            LAST_NOTIFY = datetime.now()
            with open(os.path.join(SAVE_FOLDER, fdate + ".jpg"), "rb") as f:
                r = requests.post("https://api.pushover.net/1/messages.json", data={
                    "token": NOTIFY_APP_TOKEN,
                    "user": NOTIFY_USER_TOKEN,
                    "title": "Movement Detected",
                    "url": BASE_URL + fdate,
                    "message": "Movement has been detected",
                    "url_title": "View movement (on WiFi)"
                }, files={
                    "attachment": f
                })

                print(r.content)

    LAST_FRAME = frame_gray


def camera_loop():
    i = 0
    while True:
        start = datetime.now()
        try:
            run_task()
            if i == 0:
                print("Camera motion detection took", (datetime.now() - start).total_seconds())
            i = (i + 1) % 10
            delta = (start + timedelta(seconds=2)) - datetime.now()
            if delta.total_seconds() > 0:
                time.sleep(delta.total_seconds())
            else:
                time.sleep(2)
        except Exception as e:
            print("CAMERA ERROR!")
            traceback.print_exc()
            with open("error.txt", "w") as f:
                f.write("{0}".format(e))
            time.sleep(10)


if __name__ == "__main__":
    camera_loop()
