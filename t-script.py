import subprocess
import time
import os
import json

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
LIKED_PATH = r"C:\App automation\Image Data\Liked"
DISLIKED_PATH = r"C:\App automation\Image Data\Disliked"
os.makedirs(LIKED_PATH, exist_ok=True)
os.makedirs(DISLIKED_PATH, exist_ok=True)

# Define a dictionary to store the coordinates for various actions
ACTIONS = {
    "next_image": (801, 402),
    "prev_image": (203, 405),
    "like": (685, 1775),
    "dislike": (400, 1771),
}

# Function to capture screenshot and save it with a label
def capture_screenshot(label, counters):
    if label == "like":
        counters["total_likes"] += 1
        file_path = os.path.join(LIKED_PATH, f"like_{counters["total_likes"]}.png")

    elif label == "dislike":
        counters["total_dislikes"] += 1
        file_path = os.path.join(DISLIKED_PATH, f"dislike_{counters["total_dislikes"]}.png")

    subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/temp_screenshot.png"])
    subprocess.run(["adb", "pull", "/sdcard/temp_screenshot.png", file_path])
    print(f"Saved screenshot: {file_path}")
    counters["total_images"] += 1
    save_counters(counters)

# Function to perform the swipe action
def tap(action):
    if action in ACTIONS:
        x, y = ACTIONS[action]
        subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)])
    else:
        print(f"Action '{action}' is not defined in the ACTIONS dictionary.")

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