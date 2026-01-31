"""
Take pictures with the Raspberry Pi camera module at regular intervals.

Save to a directory with timestamp.
"""

from datetime import datetime, timedelta
import gc
import time
import os
from picamera2 import Picamera2
from PIL import Image
import subprocess
import threading

PICTURE_FREQUENCY = 10 # seconds
MAX_HISTORY = 12 * 60 * 60
SAVE_DIR = "../static/pictures"
DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
ROTATE_ANGLE = -90

USE_TIMELAPSE = True
TIMELAPSE_SAVE = "../static/timelapse.mp4"
TIMELAPSE_LENGTH = 20
TIMELAPSE_FPS = 30
TIMELAPSE_TIMESTAMP_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
TIMELAPSE_GENERATE_FREQUENCY = 30 * 60 # seconds

def generate_timelapse(
    image_dir,
    output_path
):
    images = sorted(filter(lambda f: f.endswith(".jpg"), os.listdir(image_dir)))
    num_images = len(images)

    if num_images == 0:
        print("Warning: No images found for timelapse")
        return

    # Input framerate controls timelapse speed
    input_fps = num_images / TIMELAPSE_LENGTH
    if input_fps < 1:
        input_fps = 1

    use_font = True
    if not os.path.exists(TIMELAPSE_TIMESTAMP_FONT):
        use_font = False
        print("Warning: Font file not found, timestamps will not be rendered.")

    cmd = [
        "ffmpeg",
        "-y",
        "-pattern_type", "glob",
        "-framerate", str(int(input_fps)),
        "-i", os.path.join(image_dir, "*.jpg")
    ]
    if use_font:
        cmd += [
            "-vf",
            (
                "drawtext="
                f"fontfile={TIMELAPSE_TIMESTAMP_FONT}:"
                "text='%{filename}':"
                "x=20:y=h-40:"
                "fontsize=24:"
                "fontcolor=white:"
                "box=1:"
                "boxcolor=black@0.5:"
                "boxborderw=5"
            )
        ]
    
    cmd += [
        "-r", str(TIMELAPSE_FPS),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"Timelapse saved to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error in ffmpeg: {e}")

def ffmpeg_installed():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def picture_thread():
    camera = Picamera2()
    camera.configure(camera.create_still_configuration())
    camera.start()

    while True:
        filename = datetime.now().strftime(DATETIME_FORMAT)
        path = os.path.join(SAVE_DIR, f"{filename}.jpg")
        image = camera.capture_array()
        img = Image.fromarray(image).rotate(ROTATE_ANGLE, expand=True)
        img.save(path)

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
                    os.remove(os.path.join(SAVE_DIR, file))
                    print(f"Deleted old picture {file}")

        time.sleep(PICTURE_FREQUENCY)

def timelapse_thread():
    while True:
        print("Generating timelapse...")
        generate_timelapse(SAVE_DIR, TIMELAPSE_SAVE)

        time.sleep(TIMELAPSE_GENERATE_FREQUENCY)

def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    use_timelapse = USE_TIMELAPSE
    if use_timelapse and not ffmpeg_installed():
        print("Warning: ffmpeg not found, disabling timelapse generation.")
        use_timelapse = False
    
    pic_thread = threading.Thread(target=picture_thread, daemon=True)
    pic_thread.start()

    if use_timelapse:
        tl_thread = threading.Thread(target=timelapse_thread, daemon=True)
        tl_thread.start()
        tl_thread.join()

    pic_thread.join()

if __name__ == "__main__":
    main()