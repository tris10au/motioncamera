import magichue
import subprocess
from datetime import datetime, time, timedelta, date
from time import sleep
import watchdog
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager
import asyncio
import os


LIGHT_ADDR = "192.168.178.18"  # Your MagicHue lights
RESTART_NAME = "office strip"  # The name of the lights in Meross

TURN_ON = "auto"
TURN_OFF = "auto"

OFF_BRIGHTNESS = 0.10
ON_BRIGHTNESS = 0.00
TRANSITION_TIME = 45

LAST_STATE = None

TOTAL_RESTARTS = 0
RECENT_FAILS = 0
JUST_REBOOTED = False


EMAIL = os.environ.get("MEROSS_EMAIL")  # Ensure these environment variables are set
PASSWORD = os.environ.get("MEROSS_PASSWORD")


async def perform_restart():
    global EMAIL, PASSWORD, JUST_REBOOTED

    http_api_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)

    # Setup and start the device manager
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()

    # Retrieve all the MSS310 devices that are registered on this account
    await manager.async_device_discovery()
    plugs = manager.find_devices(device_type="mss310")

    if len(plugs) < 1:
        print("No MSS310 plugs found...")
    else:
        # Turn it on channel 0
        # Note that channel argument is optional for MSS310 as they only have one channel
        device = [p for p in plugs if p.name.lower() == "bathroom strip"][0]
        
        # The first time we play with a device, we must update its status
        await device.async_update()
        
        # We can now start playing with that
        print(f"Turning off {device.name}...")
        await device.async_turn_off(channel=0)
        print("Waiting a bit before turing it on")
        await asyncio.sleep(20 if JUST_REBOOTED else 5)
        print(f"Turing on {device.name}")
        await device.async_turn_on(channel=0)

    # Close the manager and logout from http_api
    manager.close()
    await http_api_client.async_logout()
    JUST_REBOOTED = True


def restart_light():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(perform_restart())


def set_light_brightness(value):
    global LIGHT_ADDR

    with watchdog.Watchdog(30):
        light = magichue.Light(LIGHT_ADDR)
        if not light.on:
            light.on = True
        light.brightness = int(255 * value)


def get_sun_times():
    cmd = subprocess.run(["./sunwait", "list", "1", "33.868820S", "151.209290E"], capture_output=True)
    sunrise, sunset = cmd.stdout.decode("utf-8").strip().split(", ")
    #print("sunrise={0}, sunset={1}".format(sunrise, sunset))
    return (
        datetime.combine(date.today(), time.fromisoformat(sunrise)),
        datetime.combine(date.today(), time.fromisoformat(sunset))
    )


def get_turn_on_time():
    global TURN_ON

    if TURN_ON == "auto":
        return get_sun_times()[0]
    return datetime.combine(date.today(), time.fromisoformat(TURN_ON))


def get_turn_off_time():
    global TURN_OFF

    if TURN_OFF == "auto":
        return get_sun_times()[1]
    return datetime.combine(date.today(), time.fromisoformat(TURN_OFF))


def desired_state(moment=None):
    if moment is None:
        moment = datetime.now()

    turn_on = get_turn_on_time()
    turn_off = get_turn_off_time()
    transition_time = timedelta(minutes=TRANSITION_TIME)

    if moment < turn_on:
        return OFF_BRIGHTNESS
    if moment > turn_off:
        return OFF_BRIGHTNESS
    if moment > (turn_on + transition_time) and moment < (turn_off - transition_time):
        return ON_BRIGHTNESS

    base_time = turn_on
    end_state = ON_BRIGHTNESS
    start_state = OFF_BRIGHTNESS
    if abs(moment - turn_on) > abs(moment - turn_off):
        base_time = turn_off
        end_state = OFF_BRIGHTNESS
        start_state = ON_BRIGHTNESS

    delta = (moment - base_time).total_seconds() / 60
    if delta <= 0:
        brightness = (end_state - start_state) * (delta / TRANSITION_TIME) + end_state
    else:
        brightness = (end_state - start_state) * (delta / TRANSITION_TIME) + start_state

    #print("delta =", delta, "bright =", brightness)


    return brightness


def set_light(brightness):
    global LAST_STATE, TOTAL_RESTARTS, RECENT_FAILS, JUST_REBOOTED

    if LAST_STATE is not None and LAST_STATE == brightness:
        print(datetime.now(), "Sleeping as no change (restarts=", TOTAL_RESTARTS, ")")
        return 1

    try:
        set_light_brightness(brightness)
        print("Set brightness to", brightness)
        LAST_STATE = brightness
        RECENT_FAILS = 0
        JUST_REBOOTED = False
        return 1
    except watchdog.Watchdog:
        LAST_STATE = None
        RECENT_FAILS += 1

        if RECENT_FAILS >= 8:
            print("Restarting light due to failure")
            restart_light()
            RECENT_FAILS = 0
            TOTAL_RESTARTS += 1
        else:
            print("Failed but not restarting yet:", RECENT_FAILS)
            return 1
        return 0


def run_task():
    state = desired_state()
    print(state)
    return set_light(state)


if __name__ == "__main__":
    while True:
        desired = datetime.now() + timedelta(minutes=1)
        result = 0
        try:
            result = run_task()
        except Exception as e:
            print("ERROR: ", e)
            result = 0
        delta = desired - datetime.now()
        if delta.total_seconds() > 0 and result > 0:
            sleep(delta.total_seconds())
        else:
            sleep(10)

    start = datetime.combine(date.today(), datetime.min.time())
    for i in range(0, 24 * 60, 10):
        t = start + timedelta(minutes=i)
        print(t.time(), "=", desired_state(t))
