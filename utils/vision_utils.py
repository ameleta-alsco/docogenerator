import cv2
from PIL import Image
from google.cloud import vision
import os
import json
from google.oauth2 import service_account

def get_google_credentials():
    # First try to get credentials from environment variable
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if credentials_json:
        try:
            # Parse the JSON string from environment variable
            credentials_info = json.loads(credentials_json)
            return service_account.Credentials.from_service_account_info(credentials_info)
        except json.JSONDecodeError:
            print("Warning: Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable")
    
    # Fallback to file if environment variable is not set or invalid
    credentials_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'idyllic-root-415700-1182fafe8fdE.json')
    if os.path.exists(credentials_file):
        return service_account.Credentials.from_service_account_file(credentials_file)
    
    raise ValueError("No valid Google Cloud credentials found. Please set GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable or provide a valid credentials file.")

def prepare_image(input_image_path, vision_client):
    if vision_client is None:
        raise ValueError("Google Cloud Vision client not initialized. Please check your credentials.")
        
    # Load the image
    image = cv2.imread(input_image_path)
    
    # Convert to RGB for Google Cloud Vision
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Convert to bytes for Google Cloud Vision
    success, buffer = cv2.imencode('.jpg', image_rgb)
    content = buffer.tobytes()
    
    # Create image object for Google Cloud Vision
    image = vision.Image(content=content)
    
    # Perform text detection
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations
    
    if not texts:
        return None, {}
        
    # Group words into lines based on y-coordinates
    lines = {}
    for text in texts[1:]:  # Skip the first element as it contains all text
        vertices = text.bounding_poly.vertices
        # Calculate bounding box dimensions
        x = vertices[0].x
        y = vertices[0].y
        width = vertices[1].x - vertices[0].x
        height = vertices[2].y - vertices[0].y
        
        # Group by y-coordinate (with some tolerance for line alignment)
        y_key = round(y)
        if y_key not in lines:
            lines[y_key] = []
        lines[y_key].append((text.description, x, width, height))
    
    print(lines)

    # Convert image to RGB to avoid palette color issues
    original_pil = Image.open(input_image_path).convert("RGB")
    
    return original_pil, lines 