import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from reader import extract_cards_from_image

# Use your test image path here
image_path = "sample_card_area.png"

# Run OCR
cards = extract_cards_from_image(image_path)

print("🃏 Detected cards:", cards)

