import subprocess
import time
import os
import json
from PIL import Image

# Define file paths for storing the counters
COUNTER_FILE = "counters.json"

# Initialize counters or load from file if it exists
def load_counters():
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r") as f:
            return json.load(f)
    else:
        # Return initial values if no file exists
        return {
            "total_likes": 0,
            "total_dislikes": 0,
            "total_images": 0
        }

# Save counters to the JSON file
def save_counters(counters):
    with open(COUNTER_FILE, "w") as f:
        json.dump(counters, f)

# Define paths for saving labeled data
LIKED_PATH = r"D:\Online Dating Automation\Image Data\Liked"
DISLIKED_PATH = r"D:\Online Dating Automation\Image Data\Disliked"
TEMP_SCREENSHOT_PATH = r"D:\Online Dating Automation\Image Data\Temporary Screenshots"
os.makedirs(LIKED_PATH, exist_ok=True)
os.makedirs(DISLIKED_PATH, exist_ok=True)
os.makedirs(TEMP_SCREENSHOT_PATH, exist_ok=True)

# Define a dictionary to store the coordinates for various actions
ACTIONS = {
    "next_image": (801, 402),
    "prev_image": (203, 405),
    "like": (685, 1775),
    "dislike": (400, 1771),
}

# Define the coordinates for cropping (adjust as needed)
CROP_BOX = (3, 150, 1074, 1548)

# Function to capture screenshot, crop it, and save it with a label
def capture_screenshot(label, counters):
    if label == "like":
        counters["total_likes"] += 1
        file_path = os.path.join(LIKED_PATH, f"like_{counters['total_likes']}.png")
    elif label == "dislike":
        counters["total_dislikes"] += 1
        file_path = os.path.join(DISLIKED_PATH, f"dislike_{counters['total_dislikes']}.png")

    temp_screenshot_path = os.path.join(TEMP_SCREENSHOT_PATH, "temp_screenshot.png")

    subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/temp_screenshot.png"])
    subprocess.run(["adb", "pull", "/sdcard/temp_screenshot.png", temp_screenshot_path])

    image = Image.open(temp_screenshot_path)
    cropped_image = image.crop(CROP_BOX)
    cropped_image.save(file_path)
    print(f"Saved cropped screenshot: {file_path}")

    counters["total_images"] += 1
    save_counters(counters)

    os.remove(temp_screenshot_path)
    cleanup()

# Function to perform the swipe action
def tap(action):
    if action in ACTIONS:
        x, y = ACTIONS[action]
        subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)])
    else:
        print(f"Action '{action}' is not defined in the ACTIONS dictionary.")

# Cleanup function to delete temporary files
def cleanup():
    subprocess.run(["adb", "shell", "rm", "/sdcard/temp_screenshot.png"])

# Main function to handle the user input and automate swiping
if __name__ == "__main__":
    counters = load_counters()

    try:
        while True:
            decision = input("Enter 'like' or 'dislike': ").strip().lower()
            if decision in ACTIONS:
                capture_screenshot(decision, counters)
                tap(decision)
            else:
                print("Invalid input. Please enter 'like' or 'dislike'.")
    except KeyboardInterrupt:
        print("Data collection stopped.")
    finally:
        cleanup()
        print("Cleanup complete. Temporary files deleted.")
