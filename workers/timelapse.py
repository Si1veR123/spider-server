from math import ceil
import subprocess
import os
import time
import numpy as np
from datetime import datetime, timedelta

PICTURE_DIR = "../static/pictures"
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
            f.write(f"file '{os.path.join(PICTURE_DIR, img)}'\n")

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
    images = sorted(filter(lambda f: f.endswith("_small.jpg"), os.listdir(PICTURE_DIR)))
    num_images = len(images)

    if num_images == 0:
        print("Warning: No images found for timelapse")
        return

    target_total_frames = TIMELAPSE_LENGTH * TIMELAPSE_FPS

    if num_images < target_total_frames:
        target_total_frames = num_images
        actual_length = num_images / TIMELAPSE_FPS
        print(f"Only {num_images} images available. Output will be {actual_length:.2f} seconds")

    indices = np.linspace(
        0,
        num_images - 1,
        target_total_frames,
        dtype=int
    )

    sampled_images = [images[i] for i in indices]

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

if __name__ == "__main__":
    if not ffmpeg_installed():
        print("Error: ffmpeg is not installed or not found in PATH.")
    else:
        while True:
            print("Generating timelapse...")
            start_time = time.time()
            generate_timelapse()
            took = time.time() - start_time
            print(f"Timelapse generation took {took:.2f} seconds")

            time.sleep(max(TIMELAPSE_GENERATE_FREQUENCY - took, 60))
