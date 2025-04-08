import os
import sys

# Optional: Load environment variables from .env (if needed)
# from dotenv import load_dotenv
# load_dotenv()

# If azure_ocr.py is one level above, adjust the path:
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from azure_ocr import extract_cards_from_azure  # Make sure azure_ocr.py is in the parent folder

def main():
    """
    Test script to verify that the extract_cards_from_azure function can
    successfully detect card rank + suit from a sample image.
    """

    # Path to your image
    image_path = r"C:\Users\Wyatt Carey\Desktop\poker-rta\sample_table_screenshot.png"

    # (Optional) Check environment variables if needed:
    # if not os.getenv("AZURE_KEY"):
    #     print("Warning: AZURE_KEY is not set.")
    # if not os.getenv("AZURE_ENDPOINT"):
    #     print("Warning: AZURE_ENDPOINT is not set.")

    # Attempt to extract cards with a try/except
    try:
        cards = extract_cards_from_azure(image_path)
        print("🃏 Azure Detected Cards:", cards)
    except FileNotFoundError as e:
        print(f"[Error] File not found: {e}")
    except Exception as e:
        print(f"[Error] An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
