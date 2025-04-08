import cv2
import numpy as np

def preprocess_card_image(image_path):
    image = cv2.imread(image_path)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Resize for consistency
    resized = cv2.resize(gray, (200, 300))

    # Sharpen the image
    blur = cv2.GaussianBlur(resized, (3, 3), 0)
    sharpened = cv2.addWeighted(resized, 1.5, blur, -0.5, 0)

    # Threshold to binary image (improves OCR)
    _, thresh = cv2.threshold(sharpened, 120, 255, cv2.THRESH_BINARY)

    return thresh
