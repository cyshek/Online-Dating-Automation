import subprocess
import time
import os
import json
import shutil
import uuid
import numpy as np
from PIL import Image
from io import BytesIO
from detecthearts import detect_hearts_from_screen

# File path for storing like/dislike counters
COUNTER_FILE = "counters.json"

# Paths for saving labeled data (liked, disliked profiles, and temporary screenshots)
LIKED_PATH = r"D:\Online Dating Automation\Image Data\Liked Profiles"
DISLIKED_PATH = r"D:\Online Dating Automation\Image Data\Disliked Profiles"
TEMP_SCREENSHOT_PATH = r"D:\Online Dating Automation\Image Data\Temporary Screenshots"

HEART_BUTTON_COORDS = (1017, 1029)  # This is the bottom right corner of the heart button
COLOR_THRESHOLD = 230  # Anything above this (R, G, B) is considered white

# Define the cropping box for Hinge profile images (left, upper, right, lower)
# CROP_BOX = (30, 302, 1047, 1331)
# Customize how far the crop extends from the heart icon
CROP_LEFT = 940 # How far to the LEFT of the heart to start cropping
CROP_TOP = 940  # How far ABOVE the heart to start cropping
CROP_RIGHT = 0    # How far to the RIGHT of the heart to include (0 = stop exactly at x)
CROP_BOTTOM = 0   # How far BELOW the heart to include (0 = stop exactly at y)



# Create the directories if they do not exist
for path in [LIKED_PATH, DISLIKED_PATH, TEMP_SCREENSHOT_PATH]:
    os.makedirs(path, exist_ok=True)

def load_counters():
    """
    Loads the counters from the JSON file if it exists.
    Returns a dictionary with counts for likes, dislikes, and total images.
    """
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r") as f:
            return json.load(f)
    return {"total_likes": 0, "total_dislikes": 0, "total_images": 0}

def save_counters(counters):
    """
    Saves the updated counters dictionary to the JSON file.
    """
    with open(COUNTER_FILE, "w") as f:
        json.dump(counters, f)

def create_profile_temp_folder():
    profile_folder = os.path.join(TEMP_SCREENSHOT_PATH, f"profile_{uuid.uuid4().hex}")
    os.makedirs(profile_folder, exist_ok=True)
    return profile_folder

def remove_images_in_main_profile_folder(profile_folder):
    """
    Removes only image files in the main profile folder, keeping subfolders intact.
    """  
    for item in os.listdir(profile_folder):
        item_path = os.path.join(profile_folder, item)
        if os.path.isfile(item_path):  # Only delete files, not subfolders
            os.remove(item_path)
            print(f"Deleted: {item_path}")

def is_prompt_background(image):
    if image.mode != 'RGB':
        image = image.convert('RGB')

    x, y = HEART_BUTTON_COORDS
    check_area = image.crop((x - 74, y - 74, x, y))

    cropped_pixels = np.array(check_area)
    avg_color = np.mean(cropped_pixels, axis=(0, 1))
    return all(avg_color > COLOR_THRESHOLD)

def swipe_up():
    # Coordinates based on 1080x1920 screen — adjust if needed
    x1, y1, x2, y2 = 500, 1000, 500, 500
    subprocess.run(["adb", "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), "300"])

if __name__ == "__main__":
    counters = load_counters()
    profile_folder = create_profile_temp_folder()

    output_folder = "detected_hearts"
    os.makedirs(output_folder, exist_ok=True)

    max_images = 5
    saved_images = 0

    max_hearts = 10
    total_saved = 0
    attempts = 0
    max_attempts = 10  # Prevent infinite scrolls

    try:
        while total_saved < max_hearts and attempts < max_attempts:
            result = subprocess.run(["adb", "shell", "screencap", "-p"], capture_output=True, check=True)
            screenshot_data = result.stdout.replace(b'\r\n', b'\n')
            img = Image.open(BytesIO(screenshot_data)).convert("RGB")  # Keep in memory

            # Check if this screen contains a heart icon (aka a profile photo)
            if is_prompt_background(img):
                print("Prompt detected. Skipping capture.")
            else:
                heart_coords = detect_hearts_from_screen(img, output_folder=output_folder, max_hearts=max_hearts)

                for i, (x, y) in enumerate(heart_coords):
                    print(f"Heart {i}: x={x}, y={y}")
                    left = max(0, x - CROP_LEFT)
                    upper = max(0, y - CROP_TOP)
                    right = x + CROP_RIGHT
                    lower = y + CROP_BOTTOM

                    cropped = img.crop((left, upper, right, lower))
                    cropped_path = os.path.join(profile_folder, f"img_{saved_images + 1}.png")
                    cropped.save(cropped_path)

                    print(f"Saved profile photo #{saved_images + 1}")
                    saved_images += 1


            prev_count = total_saved
            total_saved += len(heart_coords)


            if total_saved >= max_hearts:
                print("[hinge] Reached maximum heart count.")
                break

            if total_saved == prev_count:
                print("[hinge] No new hearts detected — possible bottom of profile.")
                break

            swipe_up()
            time.sleep(1.0)
            attempts += 1

        print(f"Done! Collected {saved_images} profile image(s).")
    except KeyboardInterrupt:
        print("Stopped manually.")
    finally:
        save_counters(counters)
        # remove_images_in_main_profile_folder(profile_folder)
