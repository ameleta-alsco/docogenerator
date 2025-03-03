#!/bin/bash
apt-get update && apt-get install -y tesseract-ocr
python -m flask run --host=0.0.0.0 --port=8000
