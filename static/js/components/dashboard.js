/* ==========================================================================
   Dafoor AI - Dashboard Component (Vanilla JS)
   ========================================================================== */

export async function renderDashboard(container, app) {
    let pdfs = [];
    
    // Fetch PDFs from the API
    try {
        pdfs = await app.apiFetch('/api/pdfs');
        app.state.pdfs = pdfs;
    } catch (err) {
        app.showToast("Failed to fetch PDFs: " + err.message, 'error');
    }

    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    function draw() {
        container.innerHTML = `
            <div class="dashboard-grid">
                <!-- Left Side: Upload Zone & Settings -->
                <div style="display: flex; flex-direction: column; gap: 24px;">
                    <div class="card">
                        <h3 class="card-title"><i class="fa-solid fa-cloud-arrow-up"></i> Upload Study Materials</h3>
                        <p style="margin-bottom: 20px;">Upload PDF textbooks, lecture notes, or research papers to auto-generate customized study quizzes.</p>
                        
                        <div id="drop-zone" class="upload-zone">
                            <i class="fa-solid fa-file-pdf"></i>
                            <div class="upload-text">
                                <p style="color: #ffffff; font-weight: 600;">Drag & drop your PDF here</p>
                                <p style="font-size: 0.85rem; margin-top: 4px;">or click to browse your files</p>
                            </div>
                            <input type="file" id="file-input" accept=".pdf" style="display: none;" />
                        </div>
                        
                        <!-- Uploading Indicator -->
                        <div id="upload-progress" class="hidden" style="margin-top: 20px; text-align: left;">
                            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 6px;">
                                <span id="upload-status" style="color: var(--color-primary); font-weight: 600;">Uploading file...</span>
                                <span id="upload-pct">0%</span>
                            </div>
                            <div style="width: 100%; height: 6px; background: #1f2937; border-radius: 3px; overflow: hidden;">
                                <div id="progress-bar" style="width: 0%; height: 100%; background: var(--gradient-primary); transition: width 0.1s;"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Gemini API Settings -->
                    <div class="card settings-section">
                        <h3 class="card-title"><i class="fa-solid fa-key"></i> Gemini AI Upgrade (Optional)</h3>
                        <p style="margin-bottom: 16px; font-size: 0.9rem;">By default, we generate quizzes using a local smart text parser. Paste your Google Gemini API Key below to unlock advanced LLM-based quiz generation.</p>
                        
                        <div class="form-group" style="margin-bottom: 12px;">
                            <label class="form-label" for="api-key-input">Gemini API Key</label>
                            <div style="display: flex; gap: 10px;">
                                <input 
                                    type="password" 
                                    id="api-key-input" 
                                    class="form-input" 
                                    placeholder="Enter AIzaSy..." 
                                    value="${app.state.geminiApiKey || ''}"
                                />
                                <button id="save-key-btn" class="btn btn-secondary">
                                    <i class="fa-solid fa-floppy-disk"></i> Save
                                </button>
                            </div>
                        </div>
                        <span id="key-badge" class="legend-dot" style="font-size: 0.8rem; color: #9ca3af; display: flex; align-items: center; gap: 6px;">
                            ${app.state.geminiApiKey 
                                ? '<i class="fa-solid fa-circle-check" style="color: var(--color-success)"></i> Key loaded from local storage' 
                                : '<i class="fa-solid fa-circle-info"></i> Running local parser engine'}
                        </span>
                    </div>
                </div>

                <!-- Right Side: PDF Library -->
                <div class="card" style="display: flex; flex-direction: column;">
                    <h3 class="card-title"><i class="fa-solid fa-book-bookmark"></i> Study Library</h3>
                    <p style="margin-bottom: 16px;">Select documents in the Practice tab to construct quizzes.</p>
                    
                    <div class="pdf-list" id="pdfs-container">
                        <!-- Populated by JS -->
                    </div>
                    
                    <button id="go-setup-btn" class="btn btn-primary" style="margin-top: auto; width: 100%;" ${pdfs.length === 0 ? 'disabled' : ''}>
                        <i class="fa-solid fa-graduation-cap"></i> Configure Practice Quiz
                    </button>
                </div>
            </div>
        `;

        renderPDFs();
        bindEvents();
    }

    function renderPDFs() {
        const container = document.getElementById('pdfs-container');
        if (pdfs.length === 0) {
            container.innerHTML = `
                <div class="pdf-empty">
                    <i class="fa-regular fa-folder-open" style="font-size: 2.5rem; margin-bottom: 12px; display: block;"></i>
                    No study materials uploaded yet.
                </div>
            `;
            return;
        }

        container.innerHTML = pdfs.map(pdf => `
            <div class="pdf-item" data-id="${pdf.id}">
                <div class="pdf-info">
                    <i class="fa-solid fa-file-pdf pdf-icon"></i>
                    <div class="pdf-details">
                        <h4 title="${pdf.filename}">${pdf.filename}</h4>
                        <span>Size: ${formatBytes(pdf.file_size)} • Uploaded: ${new Date(pdf.uploaded_at).toLocaleDateString()}</span>
                    </div>
                </div>
                <button class="btn btn-secondary btn-icon delete-pdf-btn" data-id="${pdf.id}" title="Delete document">
                    <i class="fa-regular fa-trash-can" style="color: var(--color-danger)"></i>
                </button>
            </div>
        `).join('');

        // Bind delete button events
        container.querySelectorAll('.delete-pdf-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = btn.getAttribute('data-id');
                if (confirm("Are you sure you want to delete this study document? All generated quizzes based on it will lose references.")) {
                    try {
                        await app.apiFetch(`/api/pdfs/${id}`, { method: 'DELETE' });
                        pdfs = pdfs.filter(p => p.id !== parseInt(id));
                        app.state.pdfs = pdfs;
                        app.showToast("Document deleted.", 'success');
                        draw();
                    } catch (err) {
                        app.showToast("Failed to delete PDF: " + err.message, 'error');
                    }
                }
            });
        });
    }

    function bindEvents() {
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const progressContainer = document.getElementById('upload-progress');
        const progressBar = document.getElementById('progress-bar');
        const uploadStatus = document.getElementById('upload-status');
        const uploadPct = document.getElementById('upload-pct');
        const saveKeyBtn = document.getElementById('save-key-btn');
        const apiKeyInput = document.getElementById('api-key-input');
        const goSetupBtn = document.getElementById('go-setup-btn');

        // Setup click mapping
        dropZone.addEventListener('click', () => fileInput.click());

        // File drag actions
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length) {
                handleUpload(files[0]);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                handleUpload(fileInput.files[0]);
            }
        });

        // Upload handler
        async function handleUpload(file) {
            if (!file.name.endsWith('.pdf')) {
                app.showToast("Only PDF files are supported.", "error");
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            progressContainer.classList.remove('hidden');
            progressBar.style.width = '0%';
            uploadStatus.innerText = "Uploading file...";
            uploadPct.innerText = "0%";

            // Custom XHR upload to support dynamic progress tracking
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/pdfs/upload', true);
            xhr.setRequestHeader('Authorization', `Bearer ${app.state.token}`);

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const percentage = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = `${percentage}%`;
                    uploadPct.innerText = `${percentage}%`;
                    if (percentage === 100) {
                        uploadStatus.innerText = "Extracting text and scanning...";
                    }
                }
            };

            xhr.onload = () => {
                progressContainer.classList.add('hidden');
                if (xhr.status === 200) {
                    const result = JSON.parse(xhr.responseText);
                    pdfs.unshift(result);
                    app.state.pdfs = pdfs;
                    app.showToast(`'${file.name}' uploaded successfully.`, 'success');
                    draw();
                } else {
                    const error = JSON.parse(xhr.responseText);
                    app.showToast(error.detail || "Upload failed.", 'error');
                }
            };

            xhr.onerror = () => {
                progressContainer.classList.add('hidden');
                app.showToast("Network upload error.", 'error');
            };

            xhr.send(formData);
        }

        // Save Gemini key
        saveKeyBtn.addEventListener('click', () => {
            const val = apiKeyInput.value.trim();
            app.state.geminiApiKey = val;
            if (val) {
                localStorage.setItem('gemini_api_key', val);
                app.showToast("Gemini API Key saved locally.", 'success');
            } else {
                localStorage.removeItem('gemini_api_key');
                app.showToast("Gemini API Key cleared. Now using default local parser.", 'info');
            }
            draw();
        });

        // Navigate to setup
        if (goSetupBtn) {
            goSetupBtn.addEventListener('click', () => {
                app.navigateTo('quiz-setup');
            });
        }
    }

    draw();
}
