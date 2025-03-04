import cv2
from PIL import Image, ImageDraw, ImageFont
import random
from datetime import datetime, timedelta
import os
import re
from google.cloud import vision

def allowed_file(filename, allowed_extensions={'png', 'jpg', 'jpeg'}):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


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
        "Alice", "Bob", "Charlie", "David", "Emma", "Frank", "Grace", "Hannah", "Isaac", "Jack", "Sandeep",
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
        "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "White", "Anthony"
    ]

    num_words = random.choice([2, 3, 4])  # Randomly decide name length
    name_parts = [random.choice(first_names)]
    
    if num_words >= 3:
        name_parts.append(random.choice(middle_names))  # Add middle name
    
    name_parts.append(random.choice(last_names))  # Add last name
    
    return " ".join(name_parts)


def generate_numeric_id(length):
    """Generate a random numeric ID with the specified length"""
    return ''.join(str(random.randint(0, 9)) for _ in range(length))


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
    return output_path 