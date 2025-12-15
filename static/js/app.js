document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('imageForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const btnLoader = document.getElementById('btnLoader');
    const errorDiv = document.getElementById('error');
    const resultsDiv = document.getElementById('results');
    const imageContainer = document.getElementById('imageContainer');
    const promptResult = document.getElementById('promptResult');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Get form values
        const imageUrl = document.getElementById('imageUrl').value.trim();
        const prompt = document.getElementById('prompt').value.trim();
        const model = document.getElementById('model').value;

        // Validate inputs
        if (!imageUrl || !prompt || !model) {
            showError('Please fill in all required fields');
            return;
        }

        // Hide previous results and errors
        hideError();
        hideResults();

        // Show loading state
        setLoadingState(true);

        try {
            // Make API request
            const response = await fetch(`/${model}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image_url: imageUrl,
                    prompt: prompt
                })
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
