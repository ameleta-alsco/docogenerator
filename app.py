import cv2
import re
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory, render_template, jsonify, send_file
import os
from werkzeug.utils import secure_filename
from google.cloud import vision
import io
from google.oauth2 import service_account
import json
import zipfile
import tempfile

app = Flask(__name__)
app.secret_key = 'AIzaSyAo-L2tvjg-l1PSES4iX3LBOITrTglhJuU'  # Required for flash messages

# Configure folders
UPLOAD_FOLDER = 'uploads'
DATA_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

# Initialize Google Cloud Vision client with credentials from environment or file
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

try:
    credentials = get_google_credentials()
    vision_client = vision.ImageAnnotatorClient(credentials=credentials)
except Exception as e:
    print(f"Warning: Failed to initialize Google Cloud Vision client: {e}")
    vision_client = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to generate a random date
def random_date(format="%B %d, %Y", start_year=2000, end_year=2030):
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    
    # Generate a random number of days within the range
    random_days = random.randint(0, (end_date - start_date).days)
    random_dt = start_date + timedelta(days=random_days)
    
    # Format the date as "Month Name Day, Year"
    return random_dt.strftime(format)


def generate_name():
    # First names
    first_names = [
        "Alice", "Bob", "Charlie", "David", "Emma", "Frank", "Grace", "Hannah", "Isaac", "Jack",
        "Katherine", "Liam", "Mason", "Noah", "Olivia", "Peter", "Quinn", "Rachel", "Sophia", "Thomas"
    ]
    # Middle names (optional)
    middle_names = [
        "James", "Elizabeth", "Alexander", "Marie", "William", "Lee", "Joseph", "Anne", "Michael", "Rose",
        "Daniel", "Nicole", "Ethan", "Marie", "Lucas", "Grace", "Carter", "Samantha", "Owen", "Rebecca"
    ]
    # Last names
    last_names = [
        "Johnson", "Smith", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Martinez",
        "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "White"
    ]

    num_words = random.choice([2, 3, 4])  # Randomly decide name length
    name_parts = [random.choice(first_names)]
    
    if num_words >= 3:
        name_parts.append(random.choice(middle_names))  # Add middle name
    
    name_parts.append(random.choice(last_names))  # Add last name
    
    return " ".join(name_parts)



def replace_text(draw, lines, old_name, new_name, x_offset=0, y_offset=0):
    words = re.split(r'[\s;]+', old_name.strip())
    
    # Remove empty strings if any
    words = [word for word in words if word]

    name_bbox, estimated_font_size = get_encompassing_box(lines, words)

    if name_bbox is not None:
        # Choose a font (adjust path as needed)
        font_path = "dejavu-sans-condensed.ttf"
        font_size = estimated_font_size
        font = ImageFont.truetype(font_path, font_size)
        # Cover the existing name with a white rectangle
        draw.rectangle([name_bbox[0], name_bbox[1], name_bbox[0] + name_bbox[2], name_bbox[1] + name_bbox[3]], fill="white")
        # Write the new name with offset
        draw.text((name_bbox[0] + x_offset, name_bbox[1] + y_offset), new_name, fill="black", font=font)


def prepare_image(input_image_path):
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


def get_encompassing_box(lines, target_words):
    word_boxes = []
    
    # Locate the words in the dictionary
    for y, words in lines.items():
        for word, x, width, height in words:
            if word in target_words:
                word_boxes.append((x, y, width, height))

    if len(word_boxes) != len(target_words):
        print("Not all words found!")
        return None, None

    # Find bounding box that covers all words
    x_min = min(x for x, y, w, h in word_boxes)
    y_min = min(y for x, y, w, h in word_boxes)
    x_max = max(x + w for x, y, w, h in word_boxes)
    y_max = max(y + h for x, y, w, h in word_boxes)

    estimated_font_size = max(box[3] for box in word_boxes) 

    return (x_min, y_min, x_max - x_min, y_max - y_min), estimated_font_size


def generate_numeric_id(length):
    """Generate a random numeric ID with the specified length"""
    return ''.join(str(random.randint(0, 9)) for _ in range(length))

def draw_certificate(original_pil, lines, additional_params=None):
    new_image = original_pil.copy()
    draw = ImageDraw.Draw(new_image)
    new_name = generate_name()
    
    # Handle additional parameters
    if additional_params:
        for param in additional_params:
            text = param['text']
            param_type = param['type']
            
            if param_type == 'date1':
                new_value = random_date(start_year=2010, end_year=2024)
            elif param_type == 'date2':
                new_value = random_date(format="%m/%d/%Y", start_year=2010, end_year=2024)
            elif param_type == 'numeric':
                new_value = generate_numeric_id(len(text))
            else:  # text type
                new_value = generate_name()
                
            replace_text(draw, lines, text, new_value)
    
    # Save the new image
    output_path = f"data/certificate_{new_name.replace(' ', '_')}.png"
    new_image.save(output_path)

def purge_data(DATA_FOLDER):
    for filename in os.listdir(DATA_FOLDER):
        file_path = os.path.join(DATA_FOLDER, filename)
        try:
            if os.path.isfile(file_path):  # Ensure it's a file, not a folder
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

DATA_FOLDER = os.path.abspath("data")  # Change this if your data folder is elsewhere


@app.route("/data/")
def list_files():
    """Lists files in the /data folder as an HTML page"""
    files = os.listdir(DATA_FOLDER)
    return "<br>".join(f'<a href="/data/{file}">{file}</a>' for file in files)
 

@app.route("/data/<path:filename>")
def serve_file(filename):
    """Serves files from the /data directory"""
    return send_from_directory(DATA_FOLDER, filename)
 

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/preview', methods=['POST'])
def preview():
    try:
        if 'template_image' not in request.files:
            return {'success': False, 'message': 'No template image uploaded'}
        
        file = request.files['template_image']
        if file.filename == '':
            return {'success': False, 'message': 'No selected file'}
        
        if not allowed_file(file.filename):
            return {'success': False, 'message': 'Invalid file type'}

        # Save the uploaded file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Get OCR data
        _, lines = prepare_image(filepath)
        
        # Extract only the text content
        texts = []
        for y_coord in lines:
            for text_info in lines[y_coord]:
                texts.append(text_info[0])  # text_info[0] contains the actual text

        # Clean up the temporary file
        os.remove(filepath)

        return {'success': True, 'texts': texts}

    except Exception as e:
        return {'success': False, 'message': str(e)}


@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Check if this is a preview request
        if request.form.get('preview') == 'true':
            return preview()
            
        # Check if file was uploaded
        if 'template_image' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No template image uploaded'
            })
        
        file = request.files['template_image']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No selected file'
            })
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': 'Invalid file type. Please upload PNG, JPG, or JPEG files only.'
            })
        
        purge_data(DATA_FOLDER)

        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Get form data
        num_certificates = int(request.form['num_certificates'])
        
        # Get additional parameters
        additional_params = []
        if 'additional_params' in request.form:
            try:
                additional_params = json.loads(request.form['additional_params'])
            except json.JSONDecodeError:
                print("Error parsing additional parameters")

        # Validate input
        if num_certificates < 1 or num_certificates > 100:
            return jsonify({
                'success': False,
                'message': 'Number of certificates must be between 1 and 100'
            })

        # Prepare the image using the uploaded template
        original_pil, lines = prepare_image(filepath)

        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)

        num_certificates = 10 if num_certificates > 10 else num_certificates

        # Generate certificates
        for _ in range(num_certificates):
            draw_certificate(original_pil, lines, additional_params)

        # Clean up the uploaded file
        os.remove(filepath)

        # Get list of generated files
        generated_files = os.listdir(DATA_FOLDER)

        return jsonify({
            'success': True,
            'message': f'Successfully generated {num_certificates} certificate(s)!',
            'files': generated_files
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating certificates: {str(e)}'
        })

@app.route('/download-all')
def download_all():
    try:
        # Create a temporary file for the zip
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, 'certificates.zip')
        
        # Create the zip file
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all files from the data directory
            for filename in os.listdir(DATA_FOLDER):
                file_path = os.path.join(DATA_FOLDER, filename)
                if os.path.isfile(file_path):
                    zipf.write(file_path, filename)
        
        # Send the zip file
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='certificates.zip'
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error creating zip file: {str(e)}'
        })
    finally:
        # Clean up the temporary zip file
        try:
            os.remove(zip_path)
        except:
            pass

if __name__ == '__main__':
    app.run(debug=True)

