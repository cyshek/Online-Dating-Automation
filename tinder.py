import subprocess
import time
import os
import json
import random
import datetime
import shutil
from PIL import Image
from io import BytesIO

# File path for storing like/dislike counters
COUNTER_FILE = "counters.json"

# Paths for saving labeled data (liked, disliked profiles, and temporary screenshots)
LIKED_PATH = r"D:\Online Dating Automation\Image Data\Liked Profiles"
DISLIKED_PATH = r"D:\Online Dating Automation\Image Data\Disliked Profiles"
TEMP_SCREENSHOT_PATH = r"D:\Online Dating Automation\Image Data\Temporary Screenshots"

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

# Define the cropping box for Tinder profile images (left, upper, right, lower)
CROP_BOX = (3, 150, 1074, 1410)

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
        cropped_image.save(save_path)

def cycle_through_images():
    """
    Cycles through images in a profile:
    - Creates a temporary folder for the profile.
    - Captures the first image.
    - Iterates through images by simulating a "next" tap and capturing screenshots.
    - Stops when the new image is similar to either the first image or the immediately previous one,
      or when the maximum number of images is reached.
    Returns the profile folder and the number of images captured.
    """
    profile_folder = create_profile_temp_folder()  # Create a folder for current profile
    
    # Create subfolders for individual image decisions
    liked_images_folder = os.path.join(profile_folder, "Liked_Images")
    disliked_images_folder = os.path.join(profile_folder, "Disliked_Images")
    os.makedirs(liked_images_folder, exist_ok=True)
    os.makedirs(disliked_images_folder, exist_ok=True)
    image_count = 1
    MAX_IMAGES = 5  # Maximum images to capture per profile

    # Paths for temporarily storing images
    temp_previous_image = os.path.join(TEMP_SCREENSHOT_PATH, "previous_image.png")
    temp_current_image = os.path.join(TEMP_SCREENSHOT_PATH, "current_image.png")

    # Capture the first image from the profile
    first_image_path = os.path.join(profile_folder, f"image_{image_count}.png")
    capture_and_crop_screenshot(first_image_path)
    label_individual_image(first_image_path, liked_images_folder, disliked_images_folder)
    image_count += 1

    # Simulate tap to move to the next image and wait for a short period
    tap("next_image")
    time.sleep(random.uniform(1, 1.5))
    capture_and_crop_screenshot(temp_current_image)

    # If the second image is similar to the first, stop image collection
    if images_are_similar(first_image_path, temp_current_image):
        return profile_folder, 1

    # Save the second image
    second_image_path = os.path.join(profile_folder, f"image_{image_count}.png")
    os.rename(temp_current_image, second_image_path)
    label_individual_image(second_image_path, liked_images_folder, disliked_images_folder)
    image_count += 1

    # Continue capturing images until maximum limit is reached or duplicate image is detected
    while image_count <= MAX_IMAGES:
        # Copy the last captured image for comparison later
        shutil.copy(os.path.join(profile_folder, f"image_{image_count - 1}.png"), temp_previous_image)

        # Move to next image
        tap("next_image")
        time.sleep(random.uniform(1, 1.5))
        capture_and_crop_screenshot(temp_current_image)

        # Compare current image with the first image and previous image
        if images_are_similar(first_image_path, temp_current_image) or images_are_similar(temp_previous_image, temp_current_image):
            break

        # Save the new unique image
        new_image_path = os.path.join(profile_folder, f"image_{image_count}.png")
        os.rename(temp_current_image, new_image_path)
        label_individual_image(new_image_path, liked_images_folder, disliked_images_folder)
        image_count += 1

    return profile_folder, image_count

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

def images_are_similar(img1_path, img2_path, threshold=0.95):
    """Compare images using histograms instead of pixel-wise difference for faster processing."""
    with Image.open(img1_path).convert("L") as img1, Image.open(img2_path).convert("L") as img2:
        h1 = img1.histogram()
        h2 = img2.histogram()
        rms = sum(1 - (abs(h1[i] - h2[i]) / max(h1[i], h2[i], 1)) for i in range(len(h1))) / len(h1)
        return rms > threshold  # Closer to 1 means more similar

def create_profile_temp_folder():
    """
    Creates a new temporary folder for storing screenshots of a single profile.
    The folder is named using the current timestamp.
    Returns the path of the created folder.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    profile_folder = os.path.join(TEMP_SCREENSHOT_PATH, f"profile_{timestamp}")
    os.makedirs(profile_folder, exist_ok=True)
    return profile_folder

def randomize_coordinates(x, y, max_variation=20):
    """
    Randomizes the given (x, y) coordinates within a maximum variation.
    This simulates human-like tapping behavior.
    Returns the new (x, y) coordinates.
    """
    return x + random.randint(-max_variation, max_variation), y + random.randint(-max_variation, max_variation)

def tap(action):
    """
    Simulates a tap on the mobile device using ADB.
    Looks up the coordinates for the specified action, randomizes them slightly,
    and then performs the tap command.
    """
    if action in ACTIONS:
        x, y = randomize_coordinates(*ACTIONS[action])
        subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], check=True)
    else:
        print(f"Action '{action}' is not defined.")

def remove_images_in_main_profile_folder(profile_folder):
    """
    Removes only image files in the main profile folder, keeping subfolders intact.
    """
    for item in os.listdir(profile_folder):
        item_path = os.path.join(profile_folder, item)
        if os.path.isfile(item_path):  # Only delete files, not subfolders
            os.remove(item_path)
            print(f"Deleted: {item_path}")

if __name__ == "__main__":
    # Load previous counters for likes, dislikes, and images processed
    counters = load_counters()
    try:
        # Main loop for processing each profile
        while True:
            # Cycle through images of the current profile and capture them
            profile_folder, image_count = cycle_through_images()

            # Automatically dislike profiles with only one image
            if image_count == 1:
                print("Automatically disliking profile with only one image.")
                tap("dislike")
                time.sleep(random.uniform(1, 1.5))
                shutil.rmtree(profile_folder)  # Remove the temporary folder for this profile
                continue

            # Ask user for decision: like or dislike the profile
            decision_key = input("Press 'F' to dislike or 'J' to like: ").strip().lower()

            if decision_key == "f":
                decision = "dislike"
            elif decision_key == "j":
                decision = "like"
            else:
                print("Invalid input. Please press 'F' to dislike or 'J' to like.")
                continue

            remove_images_in_main_profile_folder(profile_folder)

            # Update the counter based on the user's decision
            counters[f"total_{decision}s"] += 1
            new_folder_name = f"Person_{counters[f'total_{decision}s']}"

            # Determine the destination folder based on decision (liked or disliked)
            destination_folder = os.path.join(LIKED_PATH if decision == "like" else DISLIKED_PATH, new_folder_name)
            # Ensure folder name is unique by appending timestamp if necessary
            if os.path.exists(destination_folder):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                destination_folder += f"_{timestamp}"

            # Move the profile folder to the destination folder
            shutil.move(profile_folder, destination_folder)

            # Update overall image counter and save the updated counters to file
            counters["total_images"] += 1
            save_counters(counters)

            # Simulate the tap for like/dislike action on the device
            tap(decision)
            time.sleep(random.uniform(1, 1.5))

    except KeyboardInterrupt:
        # Allow graceful exit if the user stops the process
        print("Data collection stopped.")
    finally:
        save_counters(counters)
