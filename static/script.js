// script.js - Font Preview Functionality

document.addEventListener('DOMContentLoaded', function() {
    // Get the font dropdown and create a preview element
    const fontSelect = document.querySelector('select');
    const previewContainer = document.createElement('div');
    
    // Create and style the preview container
    previewContainer.id = 'font-preview';
    previewContainer.innerHTML = `
        <p class="preview-text">The quick brown fox jumps over the lazy dog.</p>
        <p class="preview-numbers">0123456789</p>
        <p class="preview-special">!@#$%^&*()_+</p>
    `;
    previewContainer.style.cssText = `
        margin-top: 20px;
        padding: 15px;
        border: 1px solid #ddd;
        border-radius: 5px;
        background-color: #f9f9f9;
        min-height: 150px;
        display: none;
    `;
    
    // Insert the preview container after the select element
    fontSelect.parentNode.insertBefore(previewContainer, fontSelect.nextSibling);
    
    // Style each option to display in its own font
    Array.from(fontSelect.options).forEach(option => {
        if (option.value) { // Skip the empty "Select a font..." option
            option.style.fontFamily = option.value;
        }
    });
    
    // Update preview when font is selected
    fontSelect.addEventListener('change', function() {
        const selectedFont = this.value;
        
        if (selectedFont) {
            // Show the preview container
            previewContainer.style.display = 'block';
            
            // Apply the selected font to the preview text
            previewContainer.style.fontFamily = selectedFont;
            
            // Optionally, update a custom property to store the current font
            document.documentElement.style.setProperty('--selected-font', selectedFont);
        } else {
            // Hide preview if "Select a font..." is chosen
            previewContainer.style.display = 'none';
        }
    });
    
    // Optional: Add a font size slider for better preview
    const sizeControl = document.createElement('div');
    sizeControl.innerHTML = `
        <label for="font-size">Font Size: <span id="size-value">16</span>px</label>
        <input type="range" id="font-size" min="8" max="72" value="16">
    `;
    sizeControl.style.marginTop = '10px';
    previewContainer.appendChild(sizeControl);
    
    // Font size slider functionality
    const sizeSlider = document.getElementById('font-size');
    const sizeValue = document.getElementById('size-value');
    
    sizeSlider.addEventListener('input', function() {
        const size = this.value;
        sizeValue.textContent = size;
        
        // Apply font size to preview text
        const previewTexts = previewContainer.querySelectorAll('p');
        previewTexts.forEach(text => {
            text.style.fontSize = `${size}px`;
        });
    });
});