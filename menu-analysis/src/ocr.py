import cv2
import numpy as np
import pytesseract


def preprocess_image(image: cv2.Mat) -> cv2.Mat:
    # Upscale the image to improve OCR accuracy
    image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply Otsu's thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def extract_raw_text(image_bytes: bytearray) -> str:
    img_nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(img_nparr, cv2.IMREAD_COLOR)
    denoised = preprocess_image(image)
    config = "--oem 3 --psm 3"
    text = pytesseract.image_to_string(denoised, lang="chi_tra+eng", config=config)
    return text
