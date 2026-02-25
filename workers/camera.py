"""
Take pictures with libcamera-still at regular intervals.
Save to a directory with timestamp.
Generate small versions for timelapse.
"""

from datetime import datetime, timedelta
import subprocess
import gc
import time
import os
from PIL import Image, ImageDraw, ImageFont

PICTURE_FREQUENCY = 10  # seconds
MAX_HISTORY = 12 * 60 * 60
SAVE_DIR = "../static/pictures"
DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
ROTATE_ANGLE = -90  # degrees
TIMESTAMP_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SMALL_SCALE = 0.3

def capture_image(path):
    """Capture a single JPEG using libcamera-still at full resolution"""
    subprocess.run(
        [
            "libcamera-still",
            "-n",             # no preview
            "-t", "1",        # 1 ms timeout, grab one frame
            "-o", path,       # output file
            "--rotation", str((ROTATE_ANGLE + 360) % 360),  # libcamera rotation
            "--quality", "90" # JPEG quality
        ],
        check=True
    )

def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    use_timestamp = False
    if os.path.exists(TIMESTAMP_FONT):
        use_timestamp = True
        font = ImageFont.truetype(TIMESTAMP_FONT, 64)

    while True:
        start = time.time()

        filename = datetime.now().strftime(DATETIME_FORMAT)
        path = os.path.join(SAVE_DIR, f"{filename}.jpg")

        # Capture using libcamera-still
        capture_image(path)

        # Open image for optional timestamp overlay
        img = Image.open(path)

        if use_timestamp:
            draw = ImageDraw.Draw(img)
            draw.text((20, img.height - 200), filename, font=font, fill="white")
            img.save(path)  # overwrite original with timestamp

        # Create small version
        width = int(img.width * SMALL_SCALE) // 2 * 2
        height = int(img.height * SMALL_SCALE) // 2 * 2

        small_img = img.resize((width, height), Image.LANCZOS)
        small_path = os.path.join(SAVE_DIR, f"{filename}_small.jpg")
        small_img.save(small_path)

        del small_img
        del img
        gc.collect()

        print(f"Captured {filename}")

        # Cleanup old pictures
        cutoff = datetime.now() - timedelta(seconds=MAX_HISTORY)
        for file in os.listdir(SAVE_DIR):
            if not file.endswith(".jpg") or file.endswith("_small.jpg"):
                continue

            timestamp_str = file[:-4]
            try:
                timestamp = datetime.strptime(timestamp_str, DATETIME_FORMAT)
            except ValueError:
                continue

            if timestamp < cutoff:
                try:
                    os.remove(os.path.join(SAVE_DIR, file))
                    os.remove(os.path.join(SAVE_DIR, f"{timestamp_str}_small.jpg"))
                    print(f"Deleted old picture {file}")
                except FileNotFoundError:
                    pass

        elapsed = time.time() - start
        time.sleep(max(1, PICTURE_FREQUENCY - elapsed))

if __name__ == "__main__":
    main()