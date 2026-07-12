/* ==========================================================================
   Dafoor AI - Quiz Setup Component (Vanilla JS)
   Language-aware: detects Arabic PDFs and offers generation options.
   ========================================================================== */

export async function renderQuizSetup(container, app) {
    let pdfs = app.state.pdfs;
    
    // Fetch PDFs if not loaded in state
    if (pdfs.length === 0) {
        try {
            pdfs = await app.apiFetch('/api/pdfs');
            app.state.pdfs = pdfs;
        } catch (err) {
            console.error("Failed to load PDFs in setup:", err);
        }
    }

    let selectedPdfId = pdfs.length > 0 ? pdfs[0].id : null;
    let selectedDifficulty = 'Medium';
    let questionCount = 10;
    let timeLimit = 15; // Minutes
    let detectedLanguage = null;  // null = unknown, 'arabic', 'english'
    let languageMode = 'arabic';  // 'arabic' | 'translate'
    let isDetecting = false;

    // Run language detection immediately if a PDF is already selected
    if (selectedPdfId) {
        detectLanguage(selectedPdfId);
    }

    async function detectLanguage(pdfId) {
        if (!pdfId) {
            detectedLanguage = null;
            renderLanguageCard();
            return;
        }
        isDetecting = true;
        renderLanguageCard();
        try {
            const result = await app.apiFetch(`/api/pdfs/${pdfId}/language`);
            detectedLanguage = result.language; // 'arabic' | 'english'
        } catch (err) {
            console.warn("Language detection failed:", err.message);
            detectedLanguage = null;
        }
        isDetecting = false;
        renderLanguageCard();
    }

    function renderLanguageCard() {
        const card = document.getElementById('language-options-card');
        if (!card) return;

        if (isDetecting) {
            card.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px; color: #9ca3af; font-size: 0.9rem;">
                    <i class="fa-solid fa-circle-notch fa-spin" style="color: var(--color-primary);"></i>
                    Detecting document language...
                </div>
            `;
            card.classList.remove('hidden');
            return;
        }

        if (detectedLanguage !== 'arabic') {
            card.classList.add('hidden');
            card.innerHTML = '';
            return;
        }

        // Arabic PDF detected — show options
        card.classList.remove('hidden');
        card.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 14px;">
                <span style="font-size: 1.4rem;">🇸🇦</span>
                <div>
                    <h4 style="color: #fff; margin-bottom: 4px; font-size: 0.95rem;">Arabic Document Detected</h4>
                    <p style="font-size: 0.85rem; margin: 0;">How would you like to generate the quiz questions?</p>
                </div>
            </div>

            <div style="display: flex; flex-direction: column; gap: 10px;">
                <label class="lang-option ${languageMode === 'arabic' ? 'selected' : ''}" id="lang-opt-arabic">
                    <input type="radio" name="lang-mode" value="arabic" ${languageMode === 'arabic' ? 'checked' : ''} style="display:none;">
                    <div class="lang-option-icon">📝</div>
                    <div class="lang-option-text">
                        <strong>Generate questions in Arabic</strong>
                        <span>Questions, choices & explanations will be in Arabic</span>
                    </div>
                    ${languageMode === 'arabic' ? '<i class="fa-solid fa-circle-check" style="color: var(--color-primary); margin-right: auto;"></i>' : ''}
                </label>

                <label class="lang-option ${languageMode === 'translate' ? 'selected' : ''}" id="lang-opt-translate">
                    <input type="radio" name="lang-mode" value="translate" ${languageMode === 'translate' ? 'checked' : ''} style="display:none;">
                    <div class="lang-option-icon">🌐</div>
                    <div class="lang-option-text">
                        <strong>Translate to English, then generate</strong>
                        <span>
                            Content is translated first, then questions are in English
                            ${!app.state.geminiApiKey ? '<br><em style="color: var(--color-warning);">⚠ Requires Gemini API Key (set on Dashboard)</em>' : ''}
                        </span>
                    </div>
                    ${languageMode === 'translate' ? '<i class="fa-solid fa-circle-check" style="color: var(--color-primary); margin-right: auto;"></i>' : ''}
                </label>
            </div>
        `;

        // Bind radio selection
        card.querySelectorAll('.lang-option').forEach(opt => {
            opt.addEventListener('click', () => {
                languageMode = opt.querySelector('input').value;
                renderLanguageCard();
            });
        });
    }

    function draw() {
        container.innerHTML = `
            <div class="setup-container">
                <div class="card">
                    <div class="auth-header" style="text-align: center;">
                        <h2>Configure Study Quiz</h2>
                        <p>Customize the AI engine settings to match your study goals</p>
                    </div>
                    
                    <form id="quiz-config-form">
                        <!-- Source Document Dropdown -->
                        <div class="form-group">
                            <label class="form-label" for="pdf-select">Select Study Source</label>
                            <select id="pdf-select" class="form-input" style="background-image: none; appearance: auto;">
                                ${pdfs.length > 0 ? '' : '<option value="">None - Fallback to General Knowledge</option>'}
                                ${pdfs.map(pdf => `
                                    <option value="${pdf.id}" ${pdf.id === selectedPdfId ? 'selected' : ''}>
                                        ${pdf.filename}
                                    </option>
                                `).join('')}
                                ${pdfs.length > 0 ? '<option value="">General Knowledge (No Document)</option>' : ''}
                            </select>
                        </div>

                        <!-- Language Options Card (shown only for Arabic PDFs) -->
                        <div id="language-options-card" class="lang-detect-card hidden"></div>
                        
                        <!-- Difficulty Tabs -->
                        <div class="form-group">
                            <label class="form-label">Difficulty Level</label>
                            <div class="tabs">
                                <button type="button" class="tab-btn ${selectedDifficulty === 'Easy' ? 'active' : ''}" data-val="Easy">Easy</button>
                                <button type="button" class="tab-btn ${selectedDifficulty === 'Medium' ? 'active' : ''}" data-val="Medium">Medium</button>
                                <button type="button" class="tab-btn ${selectedDifficulty === 'Hard' ? 'active' : ''}" data-val="Hard">Hard</button>
                            </div>
                        </div>

                        <!-- Question Count Slider -->
                        <div class="slider-container">
                            <div class="slider-header">
                                <span>Question Count</span>
                                <span class="slider-val" id="q-count-val">${questionCount} Questions</span>
                            </div>
                            <input 
                                type="range" 
                                id="q-count-input" 
                                class="range-input" 
                                min="5" 
                                max="30" 
                                step="5" 
                                value="${questionCount}"
                            />
                        </div>

                        <!-- Timer Slider -->
                        <div class="slider-container">
                            <div class="slider-header">
                                <span>Time Limit</span>
                                <span class="slider-val" id="timer-val">${timeLimit} Minutes</span>
                            </div>
                            <input 
                                type="range" 
                                id="timer-input" 
                                class="range-input" 
                                min="1" 
                                max="60" 
                                step="1" 
                                value="${timeLimit}"
                            />
                        </div>

                        <!-- CTA Button -->
                        <button type="submit" id="generate-btn" class="btn btn-primary" style="width: 100%; margin-top: 10px;">
                            <i class="fa-solid fa-wand-magic-sparkles"></i> Generate Study Quiz
                        </button>
                    </form>
                </div>
            </div>
        `;

        // After draw, render the language card content
        renderLanguageCard();
        bindEvents();
    }

    function bindEvents() {
        const form = document.getElementById('quiz-config-form');
        const pdfSelect = document.getElementById('pdf-select');
        const qCountInput = document.getElementById('q-count-input');
        const qCountVal = document.getElementById('q-count-val');
        const timerInput = document.getElementById('timer-input');
        const timerVal = document.getElementById('timer-val');
        const tabBtns = container.querySelectorAll('.tab-btn');
        const generateBtn = document.getElementById('generate-btn');

        // Dropdown selection change — trigger language detection
        pdfSelect.addEventListener('change', () => {
            selectedPdfId = pdfSelect.value ? parseInt(pdfSelect.value) : null;
            detectedLanguage = null;
            languageMode = 'arabic'; // reset mode
            detectLanguage(selectedPdfId);
        });

        // Tabs click
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedDifficulty = btn.getAttribute('data-val');
            });
        });

        // Question count slider
        qCountInput.addEventListener('input', () => {
            questionCount = parseInt(qCountInput.value);
            qCountVal.innerText = `${questionCount} Questions`;
        });

        // Timer slider
        timerInput.addEventListener('input', () => {
            timeLimit = parseInt(timerInput.value);
            timerVal.innerText = `${timeLimit} Minutes`;
        });

        // Submit form
        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            // If translate mode chosen but no Gemini key, warn
            if (detectedLanguage === 'arabic' && languageMode === 'translate' && !app.state.geminiApiKey) {
                app.showToast("Translation requires a Gemini API Key. Please add it on the Dashboard first.", 'error');
                return;
            }
            
            // Set dynamic loading visual state sequence
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Initializing AI Engine...';
            
            const loadingMessages = [
                "Scanning PDF text nodes...",
                "Detecting language & concepts...",
                "Drafting context definitions...",
                "Formulating distractors...",
                "Assembling quiz interface..."
            ];

            let messageIndex = 0;
            const messageInterval = setInterval(() => {
                if (messageIndex < loadingMessages.length) {
                    generateBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${loadingMessages[messageIndex]}`;
                    messageIndex++;
                }
            }, 1200);

            // Determine the language_mode to send
            // Only send it when we detected Arabic, otherwise send 'auto'
            const effectiveLanguageMode = (detectedLanguage === 'arabic') ? languageMode : 'auto';

            try {
                const response = await app.apiFetch('/api/quizzes/generate', {
                    method: 'POST',
                    body: JSON.stringify({
                        pdf_id: selectedPdfId,
                        num_questions: questionCount,
                        difficulty: selectedDifficulty,
                        time_limit: timeLimit,
                        gemini_api_key: app.state.geminiApiKey || null,
                        language_mode: effectiveLanguageMode
                    })
                });

                clearInterval(messageInterval);
                app.showToast("Quiz generated successfully! Starting now...", 'success');
                
                // Route to active quiz with payload
                app.navigateTo('quiz-active', response);
            } catch (err) {
                clearInterval(messageInterval);
                app.showToast("Failed to generate quiz: " + err.message, 'error');
                generateBtn.disabled = false;
                generateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Study Quiz';
            }
        });
    }

    draw();
}
