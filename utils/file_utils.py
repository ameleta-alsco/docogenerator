import os
import uuid

def generate_unique_filename(original_filename):
    """Generate a unique filename using UUID while preserving the original extension"""
    # Get the file extension from the original filename
    _, ext = os.path.splitext(original_filename)
    # Generate a new filename using UUID
    return f"{uuid.uuid4()}{ext}"

def purge_data(data_folder):
    """Delete all files in the specified data folder"""
    for filename in os.listdir(data_folder):
        file_path = os.path.join(data_folder, filename)
        try:
            if os.path.isfile(file_path):  # Ensure it's a file, not a folder
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

def ensure_directories(directories):
    """Ensure that all specified directories exist"""
    for directory in directories:
        os.makedirs(directory, exist_ok=True) 