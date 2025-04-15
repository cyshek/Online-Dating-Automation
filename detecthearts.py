import cv2
import numpy as np
import subprocess
from PIL import Image
from io import BytesIO
import os

# Load template once globally
template = cv2.imread("love_button.png", cv2.IMREAD_GRAYSCALE)
template_w, template_h = template.shape[::-1]

def detect_hearts_from_screen(output_folder="detected_hearts", max_hearts=5):
    os.makedirs(output_folder, exist_ok=True)

    # Take screenshot from ADB
    result = subprocess.run(["adb", "shell", "screencap", "-p"], capture_output=True, check=True)
    screenshot_data = result.stdout.replace(b'\r\n', b'\n')
    img = Image.open(BytesIO(screenshot_data))
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)

    # Template matching
    res = cv2.matchTemplate(img_cv, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.9
    loc = np.where(res >= threshold)

    saved = 0
    seen_coords = []

    for pt in zip(*loc[::-1]):
        if all(np.linalg.norm(np.array(pt) - np.array(prev)) > 20 for prev in seen_coords):
            seen_coords.append(pt)

            x, y = pt
            margin = 25
            crop = img.crop((x - margin, y - margin, x + template_w + margin, y + template_h + margin))
            crop.save(os.path.join(output_folder, f"heart_{saved + 1}.png"))
            saved += 1

            if saved >= max_hearts:
                break

    print(f"[detecthearts] Saved {saved} heart icon crop(s) in {output_folder}")
    return saved
