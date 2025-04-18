import subprocess
import time
import os
import json
import uuid
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw
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

def swipe_up():
    # Coordinates based on 1080x1920 screen — adjust if needed
    x1, y1, x2, y2 = 500, 1000, 500, 500
    subprocess.run(["adb", "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), "300"])

def is_grayscale_region(image, x, y, box_size=100, tolerance=10, grayscale_ratio_threshold=0.9):
    """
    Check if a square region centered at (x, y) is mostly grayscale.
    
    Parameters:
        image (PIL.Image): RGB image.
        x, y (int): Center coordinates.
        box_size (int): Width/height of the square region.
        tolerance (int): Max allowed difference between R, G, B to consider a pixel grayscale.
        grayscale_ratio_threshold (float): If this ratio of pixels are grayscale, region is considered grayscale.
    
    Returns:
        bool: True if region is grayscale-dominant, False otherwise.
    """
    half = box_size // 2
    left = max(0, x - half)
    upper = max(0, y - half)
    right = x + half
    lower = y + half

    region = image.crop((left, upper, right, lower)).convert("RGB")
    pixels = np.array(region)
    
    # Calculate absolute channel differences
    r, g, b = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
    diff_rg = np.abs(r - g)
    diff_rb = np.abs(r - b)
    diff_gb = np.abs(g - b)
    
    grayscale_mask = (diff_rg < tolerance) & (diff_rb < tolerance) & (diff_gb < tolerance)
    grayscale_ratio = np.sum(grayscale_mask) / grayscale_mask.size

    return grayscale_ratio >= grayscale_ratio_threshold

if __name__ == "__main__":
    counters = load_counters()
    profile_folder = create_profile_temp_folder()

    output_folder = "detected_hearts"
    os.makedirs(output_folder, exist_ok=True)

    max_images = 10
    saved_images = 0
    max_hearts = 10

    seen_hashes = set()  # Track unique image hashes to avoid saving duplicates

    try:
        while saved_images < max_images:
            result = subprocess.run(["adb", "shell", "screencap", "-p"], capture_output=True, check=True)
            screenshot_data = result.stdout.replace(b'\r\n', b'\n')
            img = Image.open(BytesIO(screenshot_data)).convert("RGB")  # Keep in memory

            
            heart_coords = detect_hearts_from_screen(img, output_folder=output_folder, max_hearts=max_hearts)

            newly_saved = 0
            for i, (x, y) in enumerate(heart_coords):
                print(f"Heart {i}: x={x}, y={y}")
                
                # Draw a red rectangle around the region being analyzed for grayscale
                draw = ImageDraw.Draw(img)
                box_half = 50  # Adjust if your is_grayscale_region uses a different size
                draw.rectangle([(x - box_half, y - box_half), (x + box_half, y + box_half)], outline="red", width=3)

                if is_grayscale_region(img, x, y):
                    print(f"Heart {i} likely in grayscale prompt — skipping.")
                    continue

                # Define crop box based on the heart position
                left = max(0, x - CROP_LEFT)
                upper = max(0, y - CROP_TOP)
                right = x + CROP_RIGHT
                lower = y + CROP_BOTTOM

                # Draw a red rectangle showing the crop area on the full image (for context)
                draw = ImageDraw.Draw(img)
                draw.rectangle([(left, upper), (right, lower)], outline="red", width=3)

                # Save the full screenshot with the red box
                full_img_path = os.path.join(profile_folder, f"img_{saved_images + 1}.png")
                img.save(full_img_path)
                print(f"Saved full screenshot #{saved_images + 1}")
                saved_images += 1

            swipe_up()
            time.sleep(1.0)

        print(f"Done! Collected {saved_images} profile image(s).")
    except KeyboardInterrupt:
        print("Stopped manually.")
    finally:
        save_counters(counters)
        # remove_images_in_main_profile_folder(profile_folder)
