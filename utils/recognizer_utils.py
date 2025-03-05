import os
import openai
from google.cloud import vision

def analyze_document(vision_client, image_path):
    """Extract text from document using Google Vision API"""
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    response = vision_client.text_detection(image=image)
    
    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))
    
    return response.text_annotations[0].description if response.text_annotations else ""

def extract_document_info(text):
    """Use ChatGPT to extract specific information from the text"""

    api_key = os.getenv('OPENAI_API_KEY')

    if api_key is None:
        api_key = open("sk-svcacct.txt", "r").read()

    openai.api_key = api_key
    
    system_prompt = (
        "You are a helpful assistant that extracts specific fields from certificate text. "
        "Please extract the following fields if they exist: \n"
        "1) Document ID\n"
        "2) Title\n"
        "3) Description\n"
        "4) To whom it's issued (Issued To)\n"
        "5) Issuing Authority\n"
        "6) Issued Date\n"
        "7) Expiry Date\n"
        "8) Renewal Frequency\n\n"
        "Return your answer as valid JSON with these keys:\n"
        "document_id, title, description, issued_to, issuing_authority, "
        "issued_date, expiry_date, renewal_frequency.\n"
        "If a field is not found, return its value as null."
    )
    # Define the prompt

    user_prompt = f"Here is the certificate text:\n\n{text}\n\n"
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )
        # Extract the reply text
        content = response.choices[0].message.content
        content = content.replace('```json', '').replace('```', '').strip()
        
        print(content)

        return content

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return {
            "document_id": "Error processing",
            "issued_to": "Error processing",
            "issuing_authority": "Error processing",
            "title": "Error processing",
            "description": "Error processing",
            "issued_date": "Error processing",
            "expiry_date": "Error processing",
            "renewal_frequency": "Error processing"
        } 