import subprocess
import time
import os
import json
import shutil
import uuid
import numpy as np
from PIL import Image
from io import BytesIO

# File path for storing like/dislike counters
COUNTER_FILE = "counters.json"

# Paths for saving labeled data (liked, disliked profiles, and temporary screenshots)
LIKED_PATH = r"D:\Online Dating Automation\Image Data\Liked Profiles"
DISLIKED_PATH = r"D:\Online Dating Automation\Image Data\Disliked Profiles"
TEMP_SCREENSHOT_PATH = r"D:\Online Dating Automation\Image Data\Temporary Screenshots"

HEART_BUTTON_COORDS = (1017, 1029)  # This is the bottom right corner of the heart button
COLOR_THRESHOLD = 230  # Anything above this (R, G, B) is considered white

# Define the cropping box for Hinge profile images (left, upper, right, lower)
CROP_BOX = (30, 302, 1047, 1331)

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

def is_prompt_background(image_path):
    """Checks if the area around the heart button is mostly white."""
    with Image.open(image_path) as image:
        # Convert to RGB if the image is in RGBA or any other mode
        if image.mode != 'RGB':
            image = image.convert('RGB')

        print(f"Original image size: {image.size}")  # Should match expected full screenshot dimensions

        x, y = HEART_BUTTON_COORDS
        check_area = image.crop((x - 74, y - 74, x, y))  # Small box around heart button

        # Debug: Print pixel values in the cropped area
        cropped_pixels = np.array(check_area)

        # Calculate the average color
        avg_color = np.mean(cropped_pixels, axis=(0, 1))  # Average R, G, B values
        print(f"Average color: {avg_color}")  # Debugging line to check the values

        # If all RGB values are above the threshold, it's likely white
        return all(avg_color > COLOR_THRESHOLD)

if __name__ == "__main__":
    counters = load_counters()
    profile_folder = create_profile_temp_folder()
    max_images = 5
    saved_images = 0
    scroll_attempts = 0
    max_scrolls = 10

    try:
        while saved_images < max_images and scroll_attempts < max_scrolls:
            # Take full screenshot first (not cropped)
            full_screenshot_path = os.path.join(profile_folder, f"full_{saved_images + 1}.png")
            result = subprocess.run(["adb", "shell", "screencap", "-p"], capture_output=True, check=True)
            screenshot_data = result.stdout.replace(b'\r\n', b'\n')
            with Image.open(BytesIO(screenshot_data)) as img:
                img.save(full_screenshot_path)

            # Check if this screen contains a heart icon (aka a profile photo)
            if is_prompt_background(full_screenshot_path):
                print("Prompt detected. Skipping capture.")
            else:
                # Crop and save actual photo area
                with Image.open(full_screenshot_path) as img:
                    cropped = img.crop(CROP_BOX)
                    cropped_path = os.path.join(profile_folder, f"img_{saved_images + 1}.png")
                    cropped.save(cropped_path)
                    print(f"Saved profile photo #{saved_images + 1}")
                    saved_images += 1

            # Always scroll down
            subprocess.run(["adb", "shell", "input", "swipe", "500", "1500", "500", "500", "300"])
            time.sleep(1.0)
            scroll_attempts += 1

        print(f"Done! Collected {saved_images} profile image(s).")
    except KeyboardInterrupt:
        print("Stopped manually.")
    finally:
        save_counters(counters)
        # remove_images_in_main_profile_folder(profile_folder)
