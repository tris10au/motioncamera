from flask import Flask, make_response, jsonify, send_from_directory, redirect
import camera
from PIL import Image, ImageFont, ImageDraw
import io
import os
from threading import Thread
from datetime import datetime, timedelta


DIR = "photos"
app = Flask(__name__)


def find_image(label, offset):
    global DIR

    benchmark_timestamp = datetime.now() - timedelta(days=3)
    files = sorted(
        [(f, datetime.fromtimestamp(os.path.getmtime(os.path.join(DIR, f)))) for f in os.listdir(DIR)],
        key=lambda x: x[1]
    )

    [os.remove(os.path.join(DIR, f[0])) for f in files if f[1] < benchmark_timestamp]

    files = [f[0].replace(".jpg", "") for f in files]
    index = len(files) - 1
    if label is not None:
        index = files.index(label)
    if not (0 <= index + offset < len(files)):
        return "No more photos"
    return redirect("/#" + files[index + offset])


def annotate_image(image_data, date_taken, recording=False):
    if date_taken is None:
        return ("No camera feed", 503)
    text = date_taken.strftime("%Y-%m-%d %H:%M:%S")
    if recording:
        text += " | MOTION DETECTED"

    img = Image.open(image_data)
    draw = ImageDraw.Draw(img)
    #font = ImageFont.truetype("sans-serif.ttf", 20)
    draw.text((5, 5),text,(255,255,0))

    result = io.BytesIO()
    img.save(result, format="JPEG")

    r = make_response(result.getvalue())
    r.headers.set("Content-Type", "image/jpeg")
    return r



@app.route("/")
def home():
    return app.send_static_file("index.html")

@app.route("/photos/<label>")
def photos(label):
    global DIR

    path = os.path.join(
        DIR, label.replace(".", "_").replace("/", "_").replace("\\", "_") + ".jpg"
    )
    age = datetime.fromtimestamp(os.path.getmtime(path))

    return annotate_image(path, age, True)

@app.route("/next/<label>")
def next_photo(label):
    return find_image(label, 1)

@app.route("/prev/<label>")
def prev_photo(label):
    return find_image(label, -1)

@app.route("/last")
def last_photo():
    global DIR

    benchmark_timestamp = datetime.now() - timedelta(days=3)
    files = sorted(
        [(f, datetime.fromtimestamp(os.path.getmtime(os.path.join(DIR, f)))) for f in os.listdir(DIR)],
        key=lambda x: x[1]
    )

    index = len(files) - 1
    while index > 0:
        if (files[index][1] - files[index - 1][1]).total_seconds() > 5:
           return redirect("/#" + files[index][0].replace(".jpg", ""))
        index = index - 1

    return "No captures found"

@app.route("/climate")
def get_climate():
    with open("climate/latest.json", "r") as f:
        return f.read()

@app.route("/camera")
def feed():
    age, data, recording = camera.capture_image()
    if data is None:
        return "Error no data"
    return annotate_image(data, age, recording)


if __name__ == "__main__":
    camera_thread = Thread(target=camera.camera_loop)
    camera_thread.start()

    app.run(host="0.0.0.0", port=8080)

