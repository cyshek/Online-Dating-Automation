import subprocess
import time
import os
import json
import random
import datetime
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
os.makedirs(LIKED_PATH, exist_ok=True)
os.makedirs(DISLIKED_PATH, exist_ok=True)
os.makedirs(TEMP_SCREENSHOT_PATH, exist_ok=True)

# Define screen coordinates for different actions on the mobile device
ACTIONS = {
    "next_image": (801, 402),
    "prev_image": (203, 405),
    "like": (685, 1775),
    "dislike": (400, 1771),
}

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

def capture_and_crop_screenshot(save_path):
    """
    Captures a screenshot from the mobile device using ADB, 
    transfers it in-memory to the local machine, 
    crops it, and saves it without writing unnecessary temporary files.
    """
    # Capture screenshot on device and output it as a raw byte stream
    result = subprocess.run(["adb", "shell", "screencap", "-p"], capture_output=True, check=True)
    screenshot_data = result.stdout.replace(b'\r\n', b'\n')  # Fixes Windows line endings issue

    # Open the screenshot in-memory and crop it
    with Image.open(BytesIO(screenshot_data)) as img:
        cropped_image = img.crop(CROP_BOX)
        cropped_image.save(save_path)  # Save the cropped image to the specified path

def label_individual_image(image_path, liked_folder, disliked_folder):
    """
    Displays the current image (optional) and prompts the user to label the image.
    If the user presses 'v', the image is copied into the disliked folder.
    If the user presses 'n', the image is copied into the liked folder.
    If no valid input is given, the image remains only in the main profile folder.
    """
    # Optionally, you could display the image using Image.open(image_path).show()
    decision = input(f"Image {os.path.basename(image_path)}: Press 'N' to like, 'V' to dislike, or any other key to skip: ").strip().lower()
    if decision == "n":
        destination = os.path.join(liked_folder, os.path.basename(image_path))
        shutil.copy(image_path, destination)
        print("Image labeled as liked.")
    elif decision == "v":
        destination = os.path.join(disliked_folder, os.path.basename(image_path))
        shutil.copy(image_path, destination)
        print("Image labeled as disliked.")

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
        if image.mode == 'RGBA':
            image = image.convert('RGB')

        print(f"Original image size: {image.size}")  # Should match expected full screenshot dimensions

        x, y = HEART_BUTTON_COORDS
        check_area = image.crop((x - 74, y - 74, x, y))  # Small box around heart button

        # Debug: Save the cropped area to see what's inside
        check_area.save("cropped_area.png")

        # Debug: Print pixel values in the cropped area
        cropped_pixels = np.array(check_area)

        # Calculate the average color
        avg_color = np.mean(cropped_pixels, axis=(0, 1))  # Average R, G, B values
        print(f"Average color: {avg_color}")  # Debugging line to check the values

        # If all RGB values are above the threshold, it's likely white
        return all(avg_color > COLOR_THRESHOLD)

if __name__ == "__main__":
    # Load previous counters for likes, dislikes, and images processed
    counters = load_counters()
    try:
        screenshot_path = os.path.join(TEMP_SCREENSHOT_PATH, "screenshot.png")
        capture_and_crop_screenshot(screenshot_path)  # Capture and save the image
        if is_prompt_background(screenshot_path):
            print("This is a prompt!")
        else:
            print("This is an image!")

        # adb shell input swipe x1 y1 x2 y2 duration
        # subprocess.run(["adb", "shell", "input", "swipe", "500", "1500", "500", "500", "300"])
        print("Screenshot captured and cropped.")
    except KeyboardInterrupt:
        # Allow graceful exit if the user stops the process
        print("Data collection stopped.")
    finally:
        save_counters(counters)