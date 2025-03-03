# Deployment Instructions for Azure App Service

## Prerequisites
1. Azure subscription
2. Azure CLI installed
3. Git installed
4. Python 3.8 or later installed locally

## Step 1: Prepare Your Local Environment

1. Clone the repository:
```bash
git clone https://github.com/ameleta-alsco/docogenerator.git
cd docogenerator
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Step 2: Azure Setup

1. Login to Azure CLI:
```bash
az login
```

2. Create a resource group:
```bash
az group create --name docogenerator-rg --location eastus
```

3. Create an Azure App Service plan:
```bash
az appservice plan create --name docogenerator-plan --resource-group docogenerator-rg --sku B1 --is-linux
```

4. Create a web app:
```bash
az webapp create --resource-group docogenerator-rg --plan docogenerator-plan --name docogenerator-app --runtime "PYTHON:3.9"
```

5. Configure the web app:
```bash
# Set Python version
az webapp config set --resource-group docogenerator-rg --name docogenerator-app --linux-fx-version "PYTHON:3.9"

# Enable logging
az webapp log config --resource-group docogenerator-rg --name docogenerator-app --application-logging filesystem
```

## Step 3: Configure Application Settings

1. Create a `.env` file in your project root:
```bash
FLASK_ENV=production
FLASK_APP=app.py
```

2. Set environment variables in Azure:
```bash
az webapp config appsettings set --resource-group docogenerator-rg --name docogenerator-app --settings FLASK_ENV=production FLASK_APP=app.py
```

## Step 4: Deploy the Application

1. Create a `.deployment` file in your project root:
```bash
[config]
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

2. Create a `startup.txt` file:
```bash
gunicorn --bind=0.0.0.0 --timeout 600 app:app
```

3. Update requirements.txt to include gunicorn:
```bash
echo "gunicorn==21.2.0" >> requirements.txt
```

4. Deploy using Git:
```bash
# Initialize git if not already done
git init
git add .
git commit -m "Initial commit"

# Add Azure remote
az webapp deployment source config-local-git --name docogenerator-app --resource-group docogenerator-rg
git remote add azure <URL_FROM_PREVIOUS_COMMAND>

# Push to Azure
git push azure master
```

## Step 5: Install Tesseract OCR

1. SSH into your web app:
```bash
az webapp ssh --resource-group docogenerator-rg --name docogenerator-app
```

2. Install Tesseract:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

## Step 6: Verify Deployment

1. Get your web app URL:
```bash
az webapp show --resource-group docogenerator-rg --name docogenerator-app --query defaultHostName -o tsv
```

2. Visit the URL in your browser to verify the application is running.

## Troubleshooting

1. Check application logs:
```bash
az webapp log tail --resource-group docogenerator-rg --name docogenerator-app
```

2. Common issues:
   - If the application fails to start, check the logs for Python version compatibility
   - If OCR fails, verify Tesseract installation
   - If static files are missing, ensure they're included in your git repository

## Maintenance

1. To update the application:
```bash
git add .
git commit -m "Update application"
git push azure master
```

2. To scale the application:
```bash
az appservice plan update --name docogenerator-plan --resource-group docogenerator-rg --sku S1
```

## Security Considerations

1. Set up SSL/TLS:
```bash
az webapp config ssl bind --resource-group docogenerator-rg --name docogenerator-app --certificate-name <your-cert-name>
```

2. Configure authentication if needed:
```bash
az webapp auth update --resource-group docogenerator-rg --name docogenerator-app --enabled true
```

## Clean Up

To remove all resources when you're done:
```bash
az group delete --name docogenerator-rg --yes
``` 