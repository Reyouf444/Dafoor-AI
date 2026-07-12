/* ==========================================================================
   Dafoor AI - Quiz Setup Component (Vanilla JS) — Arabic UI
   ========================================================================== */

export async function renderQuizSetup(container, app) {
    let pdfs = app.state.pdfs;
    
    // Fetch PDFs if not loaded in state
    if (pdfs.length === 0) {
        try {
            pdfs = await app.apiFetch('/api/pdfs');
            app.state.pdfs = pdfs;
        } catch (err) {
            console.error("فشل تحميل ملفات PDF في الإعداد:", err);
        }
    }

    let selectedPdfId = pdfs.length > 0 ? pdfs[0].id : null;
    let selectedDifficulty = 'Medium';
    let questionCount = 10;
    let timeLimit = 15; // Minutes

    function draw() {
        container.innerHTML = `
            <div class="setup-container">
                <div class="card">
                    <div class="auth-header" style="text-align: center;">
                        <h2>إعداد الاختبار الدراسي</h2>
                        <p>خصّص إعدادات محرك الذكاء الاصطناعي لتناسب أهدافك الدراسية</p>
                    </div>
                    
                    <form id="quiz-config-form">
                        <!-- Source Document Dropdown -->
                        <div class="form-group">
                            <label class="form-label" for="pdf-select">اختر المصدر الدراسي</label>
                            <select id="pdf-select" class="form-input" style="background-image: none; appearance: auto;">
                                ${pdfs.length > 0 ? '' : '<option value="">بدون مستند — أسئلة معرفة عامة</option>'}
                                ${pdfs.map(pdf => `
                                    <option value="${pdf.id}" ${pdf.id === selectedPdfId ? 'selected' : ''}>
                                        ${pdf.filename}
                                    </option>
                                `).join('')}
                                ${pdfs.length > 0 ? '<option value="">معرفة عامة (بدون مستند)</option>' : ''}
                            </select>
                        </div>
                        
                        <!-- Difficulty Tabs -->
                        <div class="form-group">
                            <label class="form-label">مستوى الصعوبة</label>
                            <div class="tabs">
                                <button type="button" class="tab-btn ${selectedDifficulty === 'Easy' ? 'active' : ''}" data-val="Easy">سهل</button>
                                <button type="button" class="tab-btn ${selectedDifficulty === 'Medium' ? 'active' : ''}" data-val="Medium">متوسط</button>
                                <button type="button" class="tab-btn ${selectedDifficulty === 'Hard' ? 'active' : ''}" data-val="Hard">صعب</button>
                            </div>
                        </div>

                        <!-- Question Count Slider -->
                        <div class="slider-container">
                            <div class="slider-header">
                                <span>عدد الأسئلة</span>
                                <span class="slider-val" id="q-count-val">${questionCount} سؤالاً</span>
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
                                <span>الوقت المحدد</span>
                                <span class="slider-val" id="timer-val">${timeLimit} دقيقة</span>
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
                            <i class="fa-solid fa-wand-magic-sparkles"></i> توليد الاختبار الدراسي
                        </button>
                    </form>
                </div>
            </div>
        `;

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

        // Dropdown selection change
        pdfSelect.addEventListener('change', () => {
            selectedPdfId = pdfSelect.value ? parseInt(pdfSelect.value) : null;
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
            qCountVal.innerText = `${questionCount} سؤالاً`;
        });

        // Timer slider
        timerInput.addEventListener('input', () => {
            timeLimit = parseInt(timerInput.value);
            timerVal.innerText = `${timeLimit} دقيقة`;
        });

        // Submit form
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Set dynamic loading visual state sequence
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> جارٍ تهيئة محرك الذكاء الاصطناعي...';
            
            const loadingMessages = [
                "جارٍ مسح نصوص PDF...",
                "تحليل المفاهيم الأساسية...",
                "صياغة التعريفات السياقية...",
                "إعداد الخيارات البديلة...",
                "تجميع واجهة الاختبار..."
            ];

            let messageIndex = 0;
            const messageInterval = setInterval(() => {
                if (messageIndex < loadingMessages.length) {
                    generateBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${loadingMessages[messageIndex]}`;
                    messageIndex++;
                }
            }, 1200);

            try {
                const response = await app.apiFetch('/api/quizzes/generate', {
                    method: 'POST',
                    body: JSON.stringify({
                        pdf_id: selectedPdfId,
                        num_questions: questionCount,
                        difficulty: selectedDifficulty,
                        time_limit: timeLimit,
                        gemini_api_key: app.state.geminiApiKey || null
                    })
                });

                clearInterval(messageInterval);
                app.showToast("تم توليد الاختبار بنجاح! يبدأ الآن...", 'success');
                
                // Route to active quiz with payload
                app.navigateTo('quiz-active', response);
            } catch (err) {
                clearInterval(messageInterval);
                app.showToast("فشل توليد الاختبار: " + err.message, 'error');
                generateBtn.disabled = false;
                generateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> توليد الاختبار الدراسي';
            }
        });
    }

    draw();
}
