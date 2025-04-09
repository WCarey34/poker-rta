from ultralytics import YOLO
import cv2
import cvzone
import math
from core.PokerHandDetector import find_poker_hand
import os

# Load YOLO model
model = YOLO("models/best.pt")  # Adjust path if needed
classNames = [...]  # Paste your full class list here

# Load your test image
image_path = "test_data/screenshot.jpg"  # <-- update this
if not os.path.exists(image_path):
    raise FileNotFoundError("Test image not found!")

img = cv2.imread(image_path)
results = model(img, stream=True)
hand = []

for r in results:
    for box in r.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        cls = int(box.cls[0])
        label = classNames[cls]

        if conf > 0.5:
            hand.append(label)
            cvzone.cornerRect(img, (x1, y1, x2 - x1, y2 - y1))
            cvzone.putTextRect(img, f"{label} {conf:.2f}", (x1, max(35, y1)), scale=1, thickness=1)

hand = list(set(hand))
print("Detected:", hand)

if len(hand) == 5:
    hand_rank = find_poker_hand.findPokerHand(hand)
    cvzone.putTextRect(img, f"Your Hand: {hand_rank}", (300, 75), scale=2, thickness=3)

cv2.imshow("Image Detection", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
