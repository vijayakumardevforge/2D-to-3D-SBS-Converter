document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    
    const uploadSection = document.getElementById('upload-section');
    const processingSection = document.getElementById('processing-section');
    const resultSection = document.getElementById('result-section');
    
    const progressBar = document.getElementById('progress-bar');
    const statusText = document.getElementById('status-text');
    
    const downloadLink = document.getElementById('download-link');
    const convertAnotherBtn = document.getElementById('convert-another-btn');
    const cancelBtn = document.getElementById('cancel-btn');

    let currentJobId = null;
    let currentPollInterval = null;

    // Replace with your actual backend URL once deployed
    const BACKEND_URL = 'http://127.0.0.1:5000/convert'; 

    // File selection logic
    browseBtn.addEventListener('click', (e) => {
        e.preventDefault();
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFile(fileInput.files[0]);
        }
    });

    // Drag and drop logic
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files; // Assign to input
            handleFile(files[0]);
        }
    });

    function switchSection(activeSection) {
        uploadSection.classList.remove('active');
        uploadSection.classList.add('hidden');
        processingSection.classList.remove('active');
        processingSection.classList.add('hidden');
        resultSection.classList.remove('active');
        resultSection.classList.add('hidden');

        activeSection.classList.remove('hidden');
        activeSection.classList.add('active');
    }

    function handleFile(file) {
        // Validate file type
        if (!file.type.startsWith('video/')) {
            alert('Please select a valid video file.');
            return;
        }

        switchSection(processingSection);
        uploadAndProcess(file);
    }

    async function uploadAndProcess(file) {
        const formData = new FormData();
        formData.append('video', file);

        try {
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    progressBar.style.width = percentComplete + '%';
                    
                    if (percentComplete < 100) {
                        statusText.textContent = `Uploading: ${Math.round(percentComplete)}%`;
                    } else {
                        progressBar.style.width = '0%';
                        progressBar.style.background = 'linear-gradient(90deg, var(--accent-secondary), var(--accent-primary))';
                        statusText.textContent = 'Starting processing...';
                    }
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    const response = JSON.parse(xhr.responseText);
                    
                    if (response.success && response.job_id) {
                        pollProgress(response.job_id, file.name);
                    } else {
                        handleError(response.message || 'Conversion failed to start');
                    }
                } else {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        handleError(response.message || 'Server error during upload');
                    } catch (e) {
                        handleError('Server error during upload');
                    }
                }
            });

            xhr.addEventListener('error', () => {
                handleError('Network error occurred during upload.');
            });

            xhr.open('POST', BACKEND_URL);
            xhr.send(formData);

        } catch (error) {
            handleError(error.message);
        }
    }

    async function pollProgress(jobId, originalFilename) {
        currentJobId = jobId;
        const progressUrl = BACKEND_URL.replace('/convert', '/progress/') + jobId;
        
        currentPollInterval = setInterval(async () => {
            try {
                const response = await fetch(progressUrl);
                const data = await response.json();
                
                if (data.success) {
                    const job = data.job;
                    
                    if (job.status === 'processing') {
                        progressBar.style.width = job.progress + '%';
                        statusText.textContent = `Conversion Progress: ${job.progress}%`;
                    } else if (job.status === 'completed') {
                        clearInterval(currentPollInterval);
                        downloadLink.href = job.download_url;
                        downloadLink.download = `3D_SBS_${originalFilename}`;
                        switchSection(resultSection);
                    } else if (job.status === 'failed') {
                        clearInterval(currentPollInterval);
                        handleError(job.message || 'Conversion failed during processing');
                    } else if (job.status === 'cancelled') {
                        clearInterval(currentPollInterval);
                        handleError(job.message || 'Conversion Cancelled');
                    }
                } else {
                    clearInterval(currentPollInterval);
                    handleError('Failed to fetch progress');
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, 1000);
    }

    function handleError(msg) {
        alert(`Error: ${msg}`);
        switchSection(uploadSection);
        progressBar.style.width = '0%';
    }

    convertAnotherBtn.addEventListener('click', () => {
        fileInput.value = '';
        progressBar.style.width = '0%';
        progressBar.style.background = 'linear-gradient(90deg, var(--accent-primary), var(--accent-secondary))';
        statusText.textContent = 'Uploading...';
        switchSection(uploadSection);
    });

    cancelBtn.addEventListener('click', async () => {
        if (!currentJobId) return;
        
        const cancelUrl = BACKEND_URL.replace('/convert', '/cancel/') + currentJobId;
        try {
            const response = await fetch(cancelUrl, { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                if (currentPollInterval) clearInterval(currentPollInterval);
                handleError('Conversion Cancelled');
            }
        } catch (e) {
            console.error("Cancel failed:", e);
        }
    });
});
