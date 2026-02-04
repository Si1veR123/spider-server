"""
Take pictures with the Raspberry Pi camera module at regular intervals.
Save to a directory with timestamp.

Generate a timelapse video from the pictures at regular intervals.
"""

from datetime import datetime, timedelta
import gc
import time
import os
from picamera2 import Picamera2
from PIL import Image, ImageDraw, ImageFont

PICTURE_FREQUENCY = 10 # seconds
MAX_HISTORY = 12 * 60 * 60
SAVE_DIR = "../static/pictures"
DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
ROTATE_ANGLE = -90
TIMESTAMP_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SMALL_SCALE = 0.3 # scale for small images for timelapse

def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    camera = Picamera2()
    camera.configure(camera.create_still_configuration())
    camera.start()

    use_timestamp = False
    if os.path.exists(TIMESTAMP_FONT):
        use_timestamp = True
        font = ImageFont.truetype(TIMESTAMP_FONT, 64)

    while True:
        start = time.time()
        filename = datetime.now().strftime(DATETIME_FORMAT)
        path = os.path.join(SAVE_DIR, f"{filename}.jpg")
        image = camera.capture_array()

        img = Image.fromarray(image).rotate(ROTATE_ANGLE, expand=True)
        if use_timestamp:
            draw = ImageDraw.Draw(img)
            draw.text((20, img.height-200), filename, font=font, fill="white")

        img.save(path)

        # Create small version for timelapse
        width =  int(img.width * SMALL_SCALE) // 2 * 2
        height = int(img.height * SMALL_SCALE) // 2 * 2
        small_img = img.resize(
            (width, height),
            Image.LANCZOS
        )
        small_path = os.path.join(SAVE_DIR, f"{filename}_small.jpg")
        small_img.save(small_path)
        del small_img

        del image
        del img
        gc.collect()

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
                    try:
                        os.remove(os.path.join(SAVE_DIR, file))
                        os.remove(os.path.join(SAVE_DIR, f"{timestamp_str}_small.jpg"))
                        print(f"Deleted old picture {file} and small version")
                    except FileNotFoundError:
                        pass

        elapsed = time.time() - start

        time.sleep(max(1, PICTURE_FREQUENCY - elapsed))

if __name__ == "__main__":
    main()