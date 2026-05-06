import os
from dotenv import load_dotenv
from extractor import extract_content, ExtractedContent

load_dotenv()   # loads GROQ_API_KEY from .env

TEST_DIR = "./test_files"

# Map filename → MIME type for testing
TEST_FILES = {
    "sample.pdf":   "application/pdf",
    "photo.png":    "image/png",
    "notes.txt":    "text/plain",
    "report.docx":  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "data.xlsx":    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "table.csv":    "text/csv",
}


def test_file(file_name: str, mime_type: str, use_vision: bool = True):
    path = os.path.join(TEST_DIR, file_name)
    if not os.path.exists(path):
        print(f"  SKIP — file not found: {path}")
        return

    with open(path, "rb") as f:
        file_bytes = f.read()

    result = extract_content(file_bytes, file_name, mime_type, use_vision_for_images=use_vision)

    print(f"\n{'='*55}")
    print(f"File     : {result.file_name}")
    print(f"Type     : {result.file_type}")
    print(f"OCR      : {result.used_ocr}")
    print(f"Vision   : {result.used_vision}")
    print(f"Chars    : {len(result.text)}")
    if result.error:
        print(f"Error    : {result.error}")
    else:
        print(f"Preview  : {result.text[:200]}...")


if __name__ == "__main__":
    os.makedirs(TEST_DIR, exist_ok=True)
    print(f"Running Phase 2 tests on files in: {TEST_DIR}\n")

    for fname, mime in TEST_FILES.items():
        test_file(fname, mime, use_vision=True)

    print("\nDone.")
