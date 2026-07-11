/* ==========================================================================
   Dafoor AI - Dashboard Component (Vanilla JS)
   ========================================================================== */

import { PDFDocument } from 'pdf-lib';

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
                handleFileSelected(files[0]);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                handleFileSelected(fileInput.files[0]);
            }
        });

        // ── PDF Size Gate ─────────────────────────────────────────────────────
        // Entry point: called whenever a file is chosen (drop or browse)
        async function handleFileSelected(file) {
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                app.showToast('Only PDF files are supported.', 'error');
                return;
            }

            const LIMIT_BYTES = 30 * 1024 * 1024; // 30 MB

            if (file.size > LIMIT_BYTES) {
                // File is too large — open the splitter modal
                await showSplitterModal(file);
            } else {
                // File is within limit — upload directly
                await uploadToGCS(file, file.name);
            }
        }

        // ── PDF Splitter Modal ────────────────────────────────────────────────
        async function showSplitterModal(file) {
            // Read total page count with pdf-lib
            let totalPages = '?';
            try {
                const arrayBuffer = await file.arrayBuffer();
                const pdfDoc = await PDFDocument.load(arrayBuffer, { ignoreEncryption: true });
                totalPages = pdfDoc.getPageCount();
            } catch (err) {
                console.warn('Could not read page count:', err);
            }

            // Inject modal into DOM
            const overlay = document.createElement('div');
            overlay.id = 'splitter-overlay';
            overlay.innerHTML = `
                <div class="splitter-modal" role="dialog" aria-modal="true" aria-labelledby="splitter-title">
                    <div class="splitter-header">
                        <i class="fa-solid fa-scissors" style="color: var(--color-primary);"></i>
                        <h3 id="splitter-title">PDF Too Large — Split It First</h3>
                    </div>

                    <p class="splitter-desc">
                        <strong title="${file.name}">${file.name.length > 45 ? file.name.slice(0, 42) + '…' : file.name}</strong>
                        is <strong>${formatBytes(file.size)}</strong>, which exceeds the 30 MB upload limit.
                        Select a page range to extract a smaller PDF and upload that instead.
                    </p>

                    <div class="splitter-info-row">
                        <span><i class="fa-regular fa-file-pdf"></i> Total pages: <strong>${totalPages}</strong></span>
                    </div>

                    <div class="splitter-range">
                        <div class="form-group">
                            <label class="form-label" for="split-start">Start Page</label>
                            <input type="number" id="split-start" class="form-input" min="1" max="${totalPages}" value="1" />
                        </div>
                        <div class="splitter-range-sep">→</div>
                        <div class="form-group">
                            <label class="form-label" for="split-end">End Page</label>
                            <input type="number" id="split-end" class="form-input" min="1" max="${totalPages}" value="${totalPages}" />
                        </div>
                    </div>

                    <p id="splitter-error" class="splitter-error hidden"></p>

                    <div class="splitter-actions">
                        <button id="splitter-cancel-btn" class="btn btn-secondary">
                            <i class="fa-solid fa-xmark"></i> Cancel
                        </button>
                        <button id="splitter-confirm-btn" class="btn btn-primary">
                            <i class="fa-solid fa-scissors"></i> Extract &amp; Upload
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            // Animate in
            requestAnimationFrame(() => overlay.classList.add('visible'));

            function closeModal() {
                overlay.classList.remove('visible');
                setTimeout(() => overlay.remove(), 300);
            }

            document.getElementById('splitter-cancel-btn').addEventListener('click', closeModal);
            overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });

            document.getElementById('splitter-confirm-btn').addEventListener('click', async () => {
                const errorEl = document.getElementById('splitter-error');
                const startVal = parseInt(document.getElementById('split-start').value, 10);
                const endVal   = parseInt(document.getElementById('split-end').value, 10);

                // Validate range
                if (isNaN(startVal) || isNaN(endVal) || startVal < 1 || endVal < startVal || endVal > totalPages) {
                    errorEl.textContent = `Please enter a valid range between 1 and ${totalPages}.`;
                    errorEl.classList.remove('hidden');
                    return;
                }
                errorEl.classList.add('hidden');

                // Update button state
                const confirmBtn = document.getElementById('splitter-confirm-btn');
                confirmBtn.disabled = true;
                confirmBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing…';

                try {
                    // ── Extract page range with pdf-lib ───────────────────────
                    const arrayBuffer = await file.arrayBuffer();
                    const srcDoc = await PDFDocument.load(arrayBuffer, { ignoreEncryption: true });

                    const newDoc = await PDFDocument.create();
                    // pdf-lib uses 0-based page indices
                    const indices = Array.from(
                        { length: endVal - startVal + 1 },
                        (_, i) => startVal - 1 + i
                    );
                    const copiedPages = await newDoc.copyPages(srcDoc, indices);
                    copiedPages.forEach(page => newDoc.addPage(page));

                    const newPdfBytes = await newDoc.save();
                    const newBlob = new Blob([newPdfBytes], { type: 'application/pdf' });

                    // Build a descriptive filename: original_p1-p5.pdf
                    const baseName = file.name.replace(/\.pdf$/i, '');
                    const newName  = `${baseName}_p${startVal}-p${endVal}.pdf`;

                    closeModal();
                    // Upload the trimmed blob
                    await uploadToGCS(newBlob, newName);

                } catch (err) {
                    errorEl.textContent = `Failed to process PDF: ${err.message}`;
                    errorEl.classList.remove('hidden');
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="fa-solid fa-scissors"></i> Extract &amp; Upload';
                }
            });
        }

        // ── GCS Signed URL Upload (3 steps) ───────────────────────────────────
        async function uploadToGCS(blob, filename) {
            progressContainer.classList.remove('hidden');
            progressBar.style.width = '5%';
            uploadStatus.innerText = 'Preparing secure upload…';
            uploadPct.innerText = '5%';

            try {
                // Step 1: Request a signed PUT URL from our backend
                const { signed_url, gcs_path } = await app.apiFetch('/api/pdfs/request-upload', {
                    method: 'POST',
                    body: JSON.stringify({ filename, file_size: blob.size })
                });

                // Step 2: PUT the blob directly to GCS (progress tracked via XHR)
                uploadStatus.innerText = 'Uploading to cloud storage…';
                await new Promise((resolve, reject) => {
                    const xhr = new XMLHttpRequest();
                    xhr.open('PUT', signed_url, true);
                    xhr.setRequestHeader('Content-Type', 'application/pdf');

                    xhr.upload.onprogress = (e) => {
                        if (e.lengthComputable) {
                            // Map XHR progress to 10–90% range for a smooth UX
                            const pct = 10 + Math.round((e.loaded / e.total) * 80);
                            progressBar.style.width = `${pct}%`;
                            uploadPct.innerText = `${pct}%`;
                        }
                    };

                    xhr.onload = () => {
                        if (xhr.status >= 200 && xhr.status < 300) resolve();
                        else reject(new Error(`GCS upload failed with status ${xhr.status}`));
                    };
                    xhr.onerror = () => reject(new Error('Network error during GCS upload.'));
                    xhr.send(blob);
                });

                // Step 3: Notify backend to record the metadata in the DB
                progressBar.style.width = '95%';
                uploadStatus.innerText = 'Finalising…';
                uploadPct.innerText = '95%';

                const result = await app.apiFetch('/api/pdfs/confirm-upload', {
                    method: 'POST',
                    body: JSON.stringify({ filename, gcs_path, file_size: blob.size })
                });

                progressBar.style.width = '100%';
                uploadPct.innerText = '100%';

                pdfs.unshift(result);
                app.state.pdfs = pdfs;
                app.showToast(`'${filename}' uploaded successfully.`, 'success');
                setTimeout(() => { progressContainer.classList.add('hidden'); draw(); }, 600);

            } catch (err) {
                progressContainer.classList.add('hidden');
                app.showToast('Upload failed: ' + err.message, 'error');
            }
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
