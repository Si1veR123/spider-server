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
from math import ceil
import subprocess
import threading

PICTURE_FREQUENCY = 10 # seconds
MAX_HISTORY = 12 * 60 * 60
SAVE_DIR = "../static/pictures"
DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
ROTATE_ANGLE = -90
TIMESTAMP_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SMALL_SCALE = 0.2 # scale for small images for timelapse

USE_TIMELAPSE = True
TIMELAPSE_SAVE_DIR = "../static/"
TIMELAPSE_LENGTH = 20
TIMELAPSE_FPS = 24
TIMELAPSE_SPLIT = 1 # seconds, split into chunks of this when processing to reduce memory usage
TIMELAPSE_GENERATE_FREQUENCY = 60 * 60 # seconds

def generate_timelapse_chunk(
    images,
    output_path
):
    chunk_txt = os.path.join(TIMELAPSE_SAVE_DIR, "chunk.txt")
    with open(chunk_txt, "w") as f:
        for img in images:
            f.write(f"file '{os.path.join(SAVE_DIR, img)}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", chunk_txt,
        "-r", str(TIMELAPSE_FPS),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error in ffmpeg chunk: {e}")
        return False

def generate_timelapse():
    images = sorted(filter(lambda f: f.endswith("_small.jpg"), os.listdir(SAVE_DIR)))
    num_images = len(images)

    if num_images == 0:
        print("Warning: No images found for timelapse")
        return

    target_total_frames = TIMELAPSE_LENGTH * TIMELAPSE_FPS

    if num_images < target_total_frames:
        target_total_frames = num_images
        actual_length = num_images / TIMELAPSE_FPS
        print(f"Only {num_images} images available. Output will be {actual_length:.2f} seconds")

    # Calculate how many input images to skip between each output frame
    step = max(1, num_images // target_total_frames)
    sampled_images = images[::step][:target_total_frames]

    frames_per_chunk = TIMELAPSE_FPS * TIMELAPSE_SPLIT
    num_chunks = ceil(len(sampled_images) / frames_per_chunk)

    chunk_files = []

    for chunk_i in range(num_chunks):
        start_idx = chunk_i * frames_per_chunk
        end_idx = min(start_idx + frames_per_chunk, len(sampled_images))
        chunk_images = sampled_images[start_idx:end_idx]

        if not chunk_images:
            continue

        chunk_output = os.path.join(TIMELAPSE_SAVE_DIR, f"timelapse_{chunk_i}.mp4")

        if generate_timelapse_chunk(
            chunk_images,
            chunk_output
        ):
            chunk_files.append(chunk_output)

    # Concatenate chunks
    concat_txt = os.path.join(TIMELAPSE_SAVE_DIR, "concat_list.txt")
    with open(concat_txt, "w") as f:
        for chunk in chunk_files:
            f.write(f"file '{chunk}'\n")

    output_path = os.path.join(TIMELAPSE_SAVE_DIR, "timelapse.mp4")
    cmd_concat = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_txt,
        "-c", "copy",
        output_path
    ]

    try:
        subprocess.run(cmd_concat, check=True)
        print(f"Timelapse saved to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error in ffmpeg concat: {e}")

def ffmpeg_installed():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def picture_thread(generate_small=False):
    camera = Picamera2()
    camera.configure(camera.create_still_configuration())
    camera.start()

    use_timestamp = False
    if os.path.exists(TIMESTAMP_FONT):
        use_timestamp = True
        font = ImageFont.truetype(TIMESTAMP_FONT, 64)

    while True:
        filename = datetime.now().strftime(DATETIME_FORMAT)
        path = os.path.join(SAVE_DIR, f"{filename}.jpg")
        image = camera.capture_array()

        img = Image.fromarray(image).rotate(ROTATE_ANGLE, expand=True)
        if use_timestamp:
            draw = ImageDraw.Draw(img)
            draw.text((20, img.height-200), filename, font=font, fill="white")

        img.save(path)

        if generate_small:
            small_img = img.resize(
                (int(img.width * SMALL_SCALE), int(img.height * SMALL_SCALE)),
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
                    os.remove(os.path.join(SAVE_DIR, file))
                    print(f"Deleted old picture {file}")

        time.sleep(PICTURE_FREQUENCY)

def timelapse_thread():
    while True:
        print("Generating timelapse...")
        generate_timelapse()

        time.sleep(TIMELAPSE_GENERATE_FREQUENCY)

def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    use_timelapse = USE_TIMELAPSE
    if use_timelapse and not ffmpeg_installed():
        print("Warning: ffmpeg not found, disabling timelapse generation.")
        use_timelapse = False
    
    pic_thread = threading.Thread(target=picture_thread, args=(use_timelapse,), daemon=True)
    pic_thread.start()

    if use_timelapse:
        tl_thread = threading.Thread(target=timelapse_thread, daemon=True)
        tl_thread.start()
        tl_thread.join()

    pic_thread.join()

if __name__ == "__main__":
    main()