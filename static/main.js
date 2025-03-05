// Function to update the left panel files list
function updateLeftPanel(files) {
    const leftPanelFilesList = document.querySelector('.left-panel .files-list');
    const panelHeader = document.querySelector('.left-panel .panel-header');
    
    if (files && files.length > 0) {
        // Update files list
        leftPanelFilesList.innerHTML = files.map(file => `
            <div class="file-item">
                <a href="/data/${file}" target="_blank" class="file-link">${file}</a>
            </div>
        `).join('');
        
        // Ensure download button exists
        if (!panelHeader.querySelector('.download-all-btn')) {
            panelHeader.innerHTML += '<a href="/download-all" class="download-all-btn">Download All (ZIP)</a>';
        }
    } else {
        leftPanelFilesList.innerHTML = '<p class="no-files">No files generated yet</p>';
        const downloadBtn = panelHeader.querySelector('.download-all-btn');
        if (downloadBtn) {
            downloadBtn.remove();
        }
    }
}

// Handle file upload and preview
document.getElementById('template_image').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('template_image', file);
    formData.append('preview', 'true');

    fetch('/generate', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        const previewContainer = document.getElementById('preview-container');
        const ocrLines = document.getElementById('ocr-lines');
        const previewImage = document.getElementById('preview-image');
        
        if (data.success) {
            previewContainer.style.display = 'block';
            previewImage.src = URL.createObjectURL(file);
            ocrLines.innerHTML = data.texts.map(text => `<div>${text}</div>`).join('');
        } else {
            previewContainer.style.display = 'none';
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error processing image');
    });
});

// Additional parameters handling
document.getElementById('add-param').addEventListener('click', function() {
    const input = document.getElementById('param-input').value;
    const type = document.getElementById('param-type').value;
    
    if (!input) {
        alert('Please enter what to replace');
        return;
    }

    const paramContainer = document.createElement('div');
    paramContainer.className = 'form-group';
    paramContainer.style.border = '1px solid #ddd';
    paramContainer.style.padding = '10px';
    paramContainer.style.marginBottom = '10px';
    paramContainer.style.borderRadius = '4px';

    const paramId = 'param-' + Date.now();
    
    paramContainer.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="flex: 1;">
                <label>Replace: ${input}</label>
                <input type="text" name="param_${paramId}_text" value="${input}" style="width: 100%;">
                <input type="hidden" name="param_${paramId}_type" value="${type}">
            </div>
            <button type="button" class="remove-param" style="width: auto; margin-left: 10px;">Remove</button>
        </div>
    `;

    document.getElementById('additional-params').appendChild(paramContainer);
    
    // Clear input
    document.getElementById('param-input').value = '';
    
    // Add remove button functionality
    paramContainer.querySelector('.remove-param').addEventListener('click', function() {
        paramContainer.remove();
    });
});

// Handle form submission
document.querySelector('form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    // Add additional parameters to formData
    const additionalParams = [];
    document.querySelectorAll('#additional-params .form-group').forEach((param) => {
        const textInput = param.querySelector('input[type="text"]');
        const typeInput = param.querySelector('input[type="hidden"]');
        additionalParams.push({
            text: textInput.value,
            type: typeInput.value
        });
    });
    
    formData.append('additional_params', JSON.stringify(additionalParams));
    
    // Show loading state
    const submitButton = this.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.textContent = 'Generating...';
    submitButton.disabled = true;
    
    // Submit the form
    fetch('/generate', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Display success message
            const resultDiv = document.createElement('div');
            resultDiv.className = 'result success';
            resultDiv.textContent = data.message;
            document.querySelector('.result')?.remove();
            document.querySelector('.container').insertBefore(resultDiv, document.getElementById('generated-files'));
            
            // Update both the main content area and left panel
            const filesList = document.getElementById('files-list');
            filesList.innerHTML = data.files.map(file => 
                `<div><a href="/data/${file}" target="_blank">${file}</a></div>`
            ).join('');
            document.getElementById('generated-files').style.display = 'block';
            
            // Update left panel
            updateLeftPanel(data.files);
        } else {
            // Display error message
            const resultDiv = document.createElement('div');
            resultDiv.className = 'result error';
            resultDiv.textContent = data.message;
            document.querySelector('.result')?.remove();
            document.querySelector('.container').insertBefore(resultDiv, document.getElementById('generated-files'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        const resultDiv = document.createElement('div');
        resultDiv.className = 'result error';
        resultDiv.textContent = 'Error generating certificates';
        document.querySelector('.result')?.remove();
        document.querySelector('.container').insertBefore(resultDiv, document.getElementById('generated-files'));
    })
    .finally(() => {
        // Reset button state
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    });
}); 