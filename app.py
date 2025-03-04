import cv2
import re
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory, render_template
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for flash messages

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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


def get_encompassing_box(lines, target_words):
    word_boxes = []
    
    # Locate the words in the dictionary
    for y, words in lines.items():
        for word, x, width, height in words:
            if word in target_words:
                word_boxes.append((x, y, width, height))

    if len(word_boxes) != len(target_words):
        print("Not all words found!")
        return None

    # Find bounding box that covers all words
    x_min = min(x for x, y, w, h in word_boxes)
    y_min = min(y for x, y, w, h in word_boxes)
    x_max = max(x + w for x, y, w, h in word_boxes)
    y_max = max(y + h for x, y, w, h in word_boxes)

    estimated_font_size = max(box[3] for box in word_boxes) 

    return (x_min, y_min, x_max - x_min, y_max - y_min), estimated_font_size


def replace_text(draw, lines, old_name, new_name, x_offset=0, y_offset=-3):
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
    # Load the image
    image = cv2.imread(input_image_path)
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply thresholding to enhance text detection
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    # Run OCR with optimized settings
    custom_oem_psm_config = r'--oem 3 --psm 6'  # OCR setting
    data = pytesseract.image_to_data(gray, config=custom_oem_psm_config, output_type=pytesseract.Output.DICT)
    # Group words into full lines
    lines = {}
    for i in range(len(data["text"])):
        word = data["text"][i].strip()
        if word:
            y = data["top"][i]
            if y not in lines:
                lines[y] = []
            lines[y].append((word, data["left"][i], data["width"][i], data["height"][i]))

    # Sort lines by y position
    #sorted_lines = sorted(lines.items())
    #print(lines)

    # Convert image to RGB to avoid palette color issues
    original_pil = Image.open(input_image_path).convert("RGB")

    return original_pil, lines


def draw_certificate(original_pil, lines, input_name, input_date, input_expire_date):
    new_image = original_pil.copy()
    draw = ImageDraw.Draw(new_image)
    new_name = generate_name()
    # Write the new name
    replace_text(draw, lines, input_name, new_name)
    # Generate issue date first
    issue_date = random_date(start_year=2010, end_year=2024)
    replace_text(draw, lines, input_date, issue_date)
    # Convert issue date string to datetime for comparison
    issue_datetime = datetime.strptime(issue_date, "%B %d, %Y")
    # Generate expiration date that's after the issue date
    replace_text(draw, lines, input_expire_date, random_date(format="%m/%d/%Y", 
                                                             start_year=issue_datetime.year,
                                                             end_year=2030))
    # Save the new image
    output_path = f"data/certificate_{new_name.replace(' ', '_')}.png"
    new_image.save(output_path)

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


@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Check if file was uploaded
        if 'template_image' not in request.files:
            return render_template('index.html',
                                 message="No template image uploaded",
                                 success=False)
        
        file = request.files['template_image']
        if file.filename == '':
            return render_template('index.html',
                                 message="No selected file",
                                 success=False)
        
        if not allowed_file(file.filename):
            return render_template('index.html',
                                 message="Invalid file type. Please upload PNG, JPG, or JPEG files only.",
                                 success=False)

        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Get form data
        num_certificates = int(request.form['num_certificates'])
        input_name = request.form['input_name']
        input_date = request.form['input_date']
        input_expire_date = request.form['input_expire_date']

        # Validate input
        if num_certificates < 1 or num_certificates > 100:
            return render_template('index.html', 
                                 message="Number of certificates must be between 1 and 100",
                                 success=False)

        # Prepare the image using the uploaded template
        original_pil, lines = prepare_image(filepath)

        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)

        # Generate certificates
        for _ in range(num_certificates):
            draw_certificate(original_pil, lines, input_name, input_date, input_expire_date)

        # Clean up the uploaded file
        os.remove(filepath)

        return render_template('index.html',
                             message=f"Successfully generated {num_certificates} certificate(s)!",
                             success=True)

    except Exception as e:
        return render_template('index.html',
                             message=f"Error generating certificates: {str(e)}",
                             success=False)

if __name__ == '__main__':
    app.run(debug=True)

