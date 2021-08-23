from lywsd03mmc import Lywsd03mmcClient
import time
import os
import json
import watchdog
from datetime import datetime, timedelta


SENSOR_ADDR = "A4:C1:38:..."  # Your sensor's MAC address here (visible in the app)
READ_FREQUENCY = 0.5 * 60  # Frequency (in mins) to check the sensor
DIR = "climate/"  # Where to store the readings

SENSOR = None
RETRIES = 0

_last = None
_last_read = None


def bounded(a, b, c):
    return min(max(a, b), c)


def read_sensor():
    global SENSOR, _last, _last_read, READ_FREQUENCY

    if _last is None or _last_read is None or (datetime.now() - _last_read).total_seconds() >= READ_FREQUENCY:
        try:
            with watchdog.Watchdog(60):
                if SENSOR is None:
                    SENSOR = Lywsd03mmcClient(SENSOR_ADDR)
                data = SENSOR.data
                if data is not None:
                    _last = data
                    _last_read = datetime.now()
                return (_last, _last_read)
        except:
            pass

    return None


def structure_reading(reading):
    return {
        "moment": reading[1].isoformat(),
        "temperature": reading[0].temperature,
        "humidity": reading[0].humidity,
        "battery": reading[0].battery
    }


def write_reading(path, reading):
    if reading is None:
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w") as f:
        json.dump(structure_reading(reading), f)


def save_reading(reading):
    global DIR

    if reading is None:
        return

    path = os.path.join(
        DIR,
        reading[1].strftime("%Y-%m-%d"),
        reading[1].strftime("%Y-%m-%d_%H-%M-%S") + ".json"
    )

    write_reading(path, reading)


def save_latest_reading(reading):
    global DIR

    if reading is None:
        return

    path = os.path.join(DIR, "latest.copy.json")
    final_path = os.path.join(DIR, "latest.json")

    write_reading(path, reading)
    os.rename(path, final_path)


def get_reading():
    print(datetime.now(), "Reading sensor...")
    result = read_sensor()
    if result is None:
        print("  Unable to read sensor")
        return False
    print("  Result:", result)
    print("  Saving reading")
    save_reading(result)
    print("  Saving as latest")
    save_latest_reading(result)
    return True


if __name__ == "__main__":
    while True:
        start = datetime.now()
        result = False
        try:
            result = get_reading()
            
        except Exception as e:
            print("ERROR: ", e)
            result = False
        delta = 60
        if result:
            RETRIES = 0
            print("Sleeping for 30")
            delta = (start + timedelta(minutes=30)) - datetime.now()
        else:
            RETRIES = bounded(1, RETRIES + 1, 20)

            if RETRIES % 2 == 0:
                SENSOR = None
                print("Resetting sensor connection")
            print("Retrying in", RETRIES + 1, "minute(s)")
            delta = (start + timedelta(minutes=RETRIES + 1)) - datetime.now()

        if delta.total_seconds() > 0:
            time.sleep(delta.total_seconds())
        else:
            print("Delta was negative, sleeping for 10, delta=", delta)
            time.sleep(10)
