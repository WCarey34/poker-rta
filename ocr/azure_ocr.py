import os
import time
import re
import cv2

from dotenv import load_dotenv
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

##############################################
# 1) Load environment variables and log them #
##############################################
load_dotenv()

AZURE_KEY = os.getenv("AZURE_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")

print(f"[DEBUG] AZURE_ENDPOINT: {AZURE_ENDPOINT}")
print(f"[DEBUG] AZURE_KEY: {AZURE_KEY[:5]+'...' if AZURE_KEY else 'None'}")  # Hides the full key for security

# Attempt to create the client
try:
    client = ComputerVisionClient(AZURE_ENDPOINT, CognitiveServicesCredentials(AZURE_KEY))
except Exception as e:
    print("[ERROR] Failed to create ComputerVisionClient. Check your endpoint/key.")
    raise

def replace_suit_symbols(text):
    """ Replace suit symbols with corresponding letters. """
    replacements = {
        "♠": "S",  # Spades
        "♥": "H",  # Hearts
        "♦": "D",  # Diamonds
        "♣": "C",  # Clubs
    }
    for symbol, letter in replacements.items():
        text = text.replace(symbol, letter)
    return text

def preprocess_image(image_path):
    """
    Reads the image from 'image_path', upscales,
    applies adaptive thresholding, and saves the result
    to 'processed_image.png'. Returns the path to processed image.
    """

    print(f"[DEBUG] Attempting to read image from '{image_path}'")
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not read image from {image_path}.")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Upscale the image so small suits won't be lost
    upscaled = cv2.resize(
        gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC
    )

    # Adaptive threshold to help preserve small glyphs
    thresh = cv2.adaptiveThreshold(
        upscaled,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,  # blockSize
        2    # constant subtracted from mean
    )

    # Write the processed image to disk
    processed_path = "processed_image.png"
    cv2.imwrite(processed_path, thresh)

    if os.path.exists(processed_path):
        size_bytes = os.path.getsize(processed_path)
        print(f"[DEBUG] Processed image saved: '{processed_path}' ({size_bytes} bytes)")
    else:
        print("[WARN] Processed image was not written to disk!")

    return processed_path

def extract_cards_from_azure(image_path):
    """
    - Preprocess the image to 'processed_image.png'.
    - Send it to Azure Computer Vision 'Read' API.
    - Parse the recognized text for card patterns.
    Returns a list of detected cards (e.g. ['3S', 'KD', ...]).
    """

    # 2) Preprocess the image and confirm the resulting file is valid
    processed_path = preprocess_image(image_path)

    # 3) Perform the Read operation on the processed file
    print(f"[DEBUG] Sending file '{processed_path}' to Azure OCR.")
    with open(processed_path, "rb") as image_stream:
        try:
            # You could remove 'language="unk"' if your resource doesn't allow it
            response = client.read_in_stream(image_stream, raw=True)
        except Exception as e:
            print("[ERROR] Azure 'read_in_stream' call failed:")
            print(e)
            raise

    # 4) Extract the operation ID for polling
    try:
        operation_location = response.headers["Operation-Location"]
        operation_id = operation_location.split("/")[-1]
    except KeyError:
        # If there's no Operation-Location header, it means the request was invalid
        print("[ERROR] 'Operation-Location' not found in response headers. Likely a 400 error.")
        raise

    # 5) Poll until the OCR operation is complete or fails
    while True:
        try:
            result = client.get_read_result(operation_id)
        except Exception as e:
            print("[ERROR] Could not retrieve read result:")
            print(e)
            raise

        if result.status not in ["notStarted", "running"]:
            break
        time.sleep(1)

    # 6) If successful, parse text for card patterns
    cards = []
    if result.status == OperationStatusCodes.succeeded:
        for page in result.analyze_result.read_results:
            for line in page.lines:
                raw_text = line.text.strip()
                print(f"[DEBUG] Azure OCR Line: '{raw_text}'")

                # Replace suit symbols
                cleaned_text = replace_suit_symbols(raw_text.upper())

                # Regex: match ranks 2-9,T,J,Q,K,A + suits H,D,C,S
                matches = re.findall(r"[2-9TJQKA][HDCS]", cleaned_text)
                if matches:
                    print(f"[DEBUG] Matched Cards: {matches}")
                    cards.extend(matches)
    else:
        print(f"[ERROR] OCR operation did not succeed, status: {result.status}")

    return cards

# Standalone test code:
if __name__ == "__main__":
    # Example usage:
    # Change this path to a real image on your system
    image_path = r"path_to_your_screenshot.png"

    try:
        detected_cards = extract_cards_from_azure(image_path)
        print("[INFO] Azure Detected Cards:", detected_cards)
    except Exception as e:
        print("[ERROR] Something went wrong during card extraction:")
        print(e)
