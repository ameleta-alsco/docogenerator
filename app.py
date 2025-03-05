from flask import Flask, render_template, request, send_from_directory, jsonify, send_file, redirect, url_for
import os
from werkzeug.utils import secure_filename
import json
import zipfile
import tempfile
from google.cloud import vision

from utils.vision_utils import get_google_credentials, prepare_image
from utils.certificate_utils import (
    allowed_file, draw_certificate
)
from utils.file_utils import purge_data, ensure_directories, generate_unique_filename
from utils.recognizer_utils import analyze_document, extract_document_info

app = Flask(__name__)
app.secret_key = 'AIzaSyAo-L2tvjg-l1PSES4iX3LBOITrTglhJuU'  # Required for flash messages

# Configure folders
UPLOAD_FOLDER = 'uploads'
DATA_FOLDER = 'data'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ensure_directories([UPLOAD_FOLDER, DATA_FOLDER])

# Initialize Google Cloud Vision client
try:
    credentials = get_google_credentials()
    vision_client = vision.ImageAnnotatorClient(credentials=credentials)
except Exception as e:
    print(f"Warning: Failed to initialize Google Cloud Vision client: {e}")
    vision_client = None

def get_data_folder_contents():
    """Get list of files in the data folder"""
    if os.path.exists(DATA_FOLDER):
        files = os.listdir(DATA_FOLDER)
        return sorted(files)
    return []

@app.route('/')
def index():
    return redirect(url_for('generator'))

@app.route('/generator')
def generator():
    files = get_data_folder_contents()
    return render_template('index.html', active_page='generator', data_files=files)

@app.route('/recognizer')
def recognizer():
    files = get_data_folder_contents()
    return render_template('recognizer.html', active_page='recognizer', data_files=files)

@app.route('/comparer')
def comparer():
    files = get_data_folder_contents()
    return render_template('comparer.html', active_page='comparer', data_files=files)

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

        # Generate a unique filename while preserving the extension
        filename = generate_unique_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Get OCR data
        _, lines = prepare_image(filepath, vision_client)
        
        # Extract only the text content
        texts = []
        for y_coord in lines:
            for text_info in lines[y_coord]:
                texts.append(text_info[0])

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

        # Generate a unique filename while preserving the extension
        filename = generate_unique_filename(file.filename)
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
        original_pil, lines = prepare_image(filepath, vision_client)

        num_certificates = min(num_certificates, 10)

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

@app.route('/data/')
def list_files():
    """Lists files in the /data folder as an HTML page"""
    files = os.listdir(DATA_FOLDER)
    return "<br>".join(f'<a href="/data/{file}">{file}</a>' for file in files)

@app.route("/data/<path:filename>")
def serve_file(filename):
    """Serves files from the /data directory"""
    return send_from_directory(DATA_FOLDER, filename)

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

@app.route('/recognize', methods=['POST'])
def recognize():
    try:
        if 'document_image' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No document image uploaded'
            })
        
        file = request.files['document_image']
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

        # Save the uploaded file temporarily
        filename = generate_unique_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Extract text using Google Vision API
            raw_text = analyze_document(vision_client, filepath)
            
            # Extract specific information using ChatGPT
            results = extract_document_info(raw_text)
            
            # Parse the JSON string from ChatGPT response
            if isinstance(results, str):
                results = json.loads(results)
            
            return jsonify({
                'success': True,
                'raw_text': raw_text,
                'results': results
            })
        finally:
            # Clean up the temporary file
            if os.path.exists(filepath):
                os.remove(filepath)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error processing document: {str(e)}'
        })

if __name__ == '__main__':
    app.run(debug=True)

