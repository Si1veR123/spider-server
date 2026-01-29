"""
Take pictures with the Raspberry Pi camera module at regular intervals.

Save to a directory with timestamp.
"""

from datetime import datetime, timedelta
import time
import os
from picamera2 import Picamera2
from PIL import Image

FREQUENCY = 10
MAX_HISTORY = 12 * 60 * 60
SAVE_DIR = "../pictures"
DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
ROTATE_ANGLE = -90

def main():
    camera = Picamera2()
    camera.configure(camera.create_still_configuration())
    camera.start()

    os.makedirs(SAVE_DIR, exist_ok=True)

    while True:
        filename = datetime.now().strftime(DATETIME_FORMAT)
        path = os.path.join(SAVE_DIR, f"{filename}.jpg")
        image = camera.capture_array()
        img = Image.fromarray(image).rotate(ROTATE_ANGLE, expand=True)
        img.save(path)

        print(f"Captured {filename}")

        # Cleanup old pictures
        cutoff = datetime.now() - timedelta(seconds=MAX_HISTORY)
        for file in os.listdir(SAVE_DIR):
            if file.endswith(".jpg"):
                timestamp_str = file[:-4]
                try:
                    timestamp = datetime.strptime(timestamp_str, DATETIME_FORMAT)
                except ValueError:
                    continue
                if timestamp < cutoff:
                    os.remove(os.path.join(SAVE_DIR, file))
                    print(f"Deleted old picture {file}")

        time.sleep(FREQUENCY)

if __name__ == "__main__":
    main()