document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('imageForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const btnLoader = document.getElementById('btnLoader');
    const errorDiv = document.getElementById('error');
    const resultsDiv = document.getElementById('results');
    const imageContainer = document.getElementById('imageContainer');
    const promptResult = document.getElementById('promptResult');
    const advancedToggle = document.getElementById('advancedToggle');
    const advancedContent = document.getElementById('advancedContent');
    const modelSelect = document.getElementById('model');

    // Upload elements
    const uploadArea = document.getElementById('uploadArea');
    const imageFile = document.getElementById('imageFile');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    const uploadPreview = document.getElementById('uploadPreview');
    const uploadProgress = document.getElementById('uploadProgress');
    const previewImage = document.getElementById('previewImage');
    const previewFilename = document.getElementById('previewFilename');
    const removeImage = document.getElementById('removeImage');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    // Store the selected file (not uploaded yet)
    let selectedFile = null;

    // Tab elements
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    // Tab switching
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            // Update tab buttons
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update tab contents
            tabContents.forEach(content => {
                const contentTab = content.getAttribute('data-tab-content');
                if (contentTab === targetTab) {
                    content.classList.add('active');
                } else {
                    content.classList.remove('active');
                }
            });

            // Clear the non-active input
            if (targetTab === 'url') {
                clearUpload();
            } else {
                document.getElementById('imageUrl').value = '';
            }
        });
    });

    // Toggle advanced options
    advancedToggle.addEventListener('click', () => {
        advancedContent.classList.toggle('hidden');
        advancedToggle.classList.toggle('active');
    });

    // Upload area click handler
    uploadArea.addEventListener('click', (e) => {
        if (!e.target.closest('.remove-btn')) {
            imageFile.click();
        }
    });

    // File input change handler
    imageFile.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFile(file);
        }
    });

    // Drag and drop handlers
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragging');
    });

    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragging');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragging');

        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            handleFile(file);
        } else {
            showError('Please drop a valid image file (JPEG or PNG)');
        }
    });

    // Remove image handler
    removeImage.addEventListener('click', (e) => {
        e.stopPropagation();
        clearUpload();
    });

    // Handle file selection (preview only, no upload yet)
    function handleFile(file) {
        // Validate file type
        const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg'];
        if (!allowedTypes.includes(file.type)) {
            showError('Invalid file type. Please upload JPEG or PNG images.');
            return;
        }

        // Validate file size (10MB)
        const maxSize = 10 * 1024 * 1024;
        if (file.size > maxSize) {
            showError('File size exceeds 10MB limit.');
            return;
        }

        // Store the file for later upload when user clicks Generate
        selectedFile = file;

        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            previewFilename.textContent = file.name;
        };
        reader.readAsDataURL(file);

        // Hide placeholder, show preview
        uploadPlaceholder.classList.add('hidden');
        uploadPreview.classList.remove('hidden');
    }

    // Clear upload state
    function clearUpload() {
        selectedFile = null;
        imageFile.value = '';
        previewImage.src = '';
        previewFilename.textContent = '';
        uploadPlaceholder.classList.remove('hidden');
        uploadPreview.classList.add('hidden');
        uploadProgress.classList.add('hidden');
        progressFill.style.width = '0%';
    }

    // Helper: Convert File to base64 string
    function fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                // Extract base64 part (remove "data:image/jpeg;base64," prefix)
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    // Handle model change to show/hide relevant options
    modelSelect.addEventListener('change', () => {
        updateVisibleOptions();
    });

    // Update visible options based on selected model
    function updateVisibleOptions() {
        const selectedModel = modelSelect.value;
        const allOptions = document.querySelectorAll('[data-models]');

        allOptions.forEach(option => {
            const supportedModels = option.getAttribute('data-models').split(',');

            if (supportedModels.includes(selectedModel)) {
                option.style.display = '';
                option.classList.remove('model-hidden');
            } else {
                option.style.display = 'none';
                option.classList.add('model-hidden');

                // Clear value when hiding to avoid sending incorrect params
                const input = option.querySelector('input, select');
                if (input) {
                    if (input.type === 'checkbox') {
                        input.checked = false;
                    } else {
                        input.value = '';
                    }
                }
            }
        });
    }

    // Initialize visible options on page load
    updateVisibleOptions();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Get form values
        const imageUrl = document.getElementById('imageUrl').value.trim();
        const prompt = document.getElementById('prompt').value.trim();
        const model = document.getElementById('model').value;

        // Validate inputs
        if ((!selectedFile && !imageUrl) || !prompt || !model) {
            showError('Please provide an image (URL or upload) and a prompt');
            return;
        }

        // Hide previous results and errors
        hideError();
        hideResults();

        // Show loading state
        setLoadingState(true);

        try {
            // Build JSON request body
            const requestBody = {
                prompt: prompt,
                ...getAdvancedOptions()
            };

            // Add either URL or base64 file data
            if (selectedFile) {
                const base64Data = await fileToBase64(selectedFile);
                requestBody.image_data = base64Data;
            } else {
                requestBody.image_url = imageUrl;
            }

            // Make API request with JSON
            const response = await fetch(`/${model}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Something went wrong');
            }

            // Display results
            displayResults(data);

        } catch (error) {
            showError(error.message || 'Failed to generate images. Please try again.');
        } finally {
            setLoadingState(false);
        }
    });

    function setLoadingState(isLoading) {
        if (isLoading) {
            submitBtn.disabled = true;
            btnText.textContent = 'Generating...';
            btnLoader.classList.remove('hidden');
        } else {
            submitBtn.disabled = false;
            btnText.textContent = 'Generate';
            btnLoader.classList.add('hidden');
        }
    }

    function showError(message) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
    }

    function hideError() {
        errorDiv.textContent = '';
        errorDiv.classList.add('hidden');
    }

    function hideResults() {
        resultsDiv.classList.add('hidden');
        imageContainer.innerHTML = '';
        promptResult.innerHTML = '';
    }

    function getAdvancedOptions() {
        const options = {};

        // Helper function to get value if not empty and element is visible
        const getValue = (id) => {
            const element = document.getElementById(id);
            if (!element) return null;

            // Check if the element's parent is hidden due to model selection
            const parent = element.closest('[data-models]');
            if (parent && parent.classList.contains('model-hidden')) {
                return null;
            }

            if (element.type === 'checkbox') {
                return element.checked ? true : null;
            }

            const value = element.value.trim();
            if (value === '' || value.startsWith('Default')) return null;

            // Convert to appropriate type
            if (element.type === 'number') {
                const num = parseFloat(value);
                return isNaN(num) ? null : num;
            }

            return value;
        };

        // Image Generation
        const numImages = getValue('numImages');
        if (numImages !== null) options.num_images = numImages;

        const seed = getValue('seed');
        if (seed !== null) options.seed = seed;

        const outputFormat = getValue('outputFormat');
        if (outputFormat !== null) options.output_format = outputFormat;

        // Quality & Performance
        const guidanceScale = getValue('guidanceScale');
        if (guidanceScale !== null) options.guidance_scale = guidanceScale;

        const numInferenceSteps = getValue('numInferenceSteps');
        if (numInferenceSteps !== null) options.num_inference_steps = numInferenceSteps;

        const acceleration = getValue('acceleration');
        if (acceleration !== null) options.acceleration = acceleration;

        // Aspect Ratio & Resolution
        const aspectRatio = getValue('aspectRatio');
        if (aspectRatio !== null) options.aspect_ratio = aspectRatio;

        const resolutionMode = getValue('resolutionMode');
        if (resolutionMode !== null) options.resolution_mode = resolutionMode;

        // Safety & Enhancement
        const safetyTolerance = getValue('safetyTolerance');
        if (safetyTolerance !== null) options.safety_tolerance = safetyTolerance;

        const enableSafetyChecker = getValue('enableSafetyChecker');
        if (enableSafetyChecker !== null) options.enable_safety_checker = enableSafetyChecker;

        const enhancePrompt = getValue('enhancePrompt');
        if (enhancePrompt !== null) options.enhance_prompt = enhancePrompt;

        const syncMode = getValue('syncMode');
        if (syncMode !== null) options.sync_mode = syncMode;

        return options;
    }

    function displayResults(data) {
        // Clear previous results
        imageContainer.innerHTML = '';
        promptResult.innerHTML = '';

        // Display images
        if (data.images && data.images.length > 0) {
            data.images.forEach((image, index) => {
                const wrapper = document.createElement('div');
                wrapper.className = 'image-wrapper';

                const img = document.createElement('img');
                img.src = image.url;
                img.alt = `Generated image ${index + 1}`;
                img.loading = 'lazy';

                const info = document.createElement('div');
                info.className = 'image-info';
                info.textContent = `${image.width} × ${image.height}`;

                wrapper.appendChild(img);
                wrapper.appendChild(info);
                imageContainer.appendChild(wrapper);
            });
        }

        // Display prompt
        if (data.prompt) {
            promptResult.innerHTML = `<strong>Enhanced Prompt:</strong> ${data.prompt}`;
        }

        // Show results section
        resultsDiv.classList.remove('hidden');

        // Scroll to results
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
});
