/* ==========================================================================
   Dafoor AI - Active Quiz & Review Component (Vanilla JS) — Arabic UI
   ========================================================================== */

export function renderQuizActive(container, app, quizData) {
    if (!quizData) {
        app.showToast("لا توجد جلسة اختبار نشطة.", 'error');
        app.navigateTo('quiz-setup');
        return;
    }

    const { quiz_id, title, time_limit, questions } = quizData;
    const totalQuestions = questions.length;
    
    // User response state
    let currentQuestionIdx = 0;
    const userAnswers = new Array(totalQuestions).fill(-1); // -1 = skipped/unanswered
    const flaggedQuestions = new Array(totalQuestions).fill(false); // true = flagged
    
    // Timer state
    let secondsRemaining = time_limit * 60;
    let timerInterval = null;

    // Start timer on rendering
    startTimer();

    function startTimer() {
        timerInterval = setInterval(() => {
            secondsRemaining--;
            updateTimerDisplay();
            
            if (secondsRemaining <= 0) {
                clearInterval(timerInterval);
                app.showToast("انتهى الوقت! جارٍ إرسال إجاباتك تلقائيًا...", 'warning');
                submitQuiz();
            }
        }, 1000);
    }

    function updateTimerDisplay() {
        const timerPanel = document.getElementById('timer-panel-el');
        const timerVal = document.getElementById('timer-val-el');
        if (!timerVal) return;

        const mins = Math.floor(secondsRemaining / 60);
        const secs = secondsRemaining % 60;
        
        // Format MM:SS
        const minStr = mins.toString().padStart(2, '0');
        const secStr = secs.toString().padStart(2, '0');
        timerVal.innerText = `${minStr}:${secStr}`;

        // Alarm state (less than 1 min left)
        if (secondsRemaining <= 60) {
            timerPanel.classList.add('warning');
        } else {
            timerPanel.classList.remove('warning');
        }
    }

    function draw() {
        container.innerHTML = `
            <div class="quiz-active-grid">
                <!-- Left Side: Question area -->
                <div class="card" id="question-card">
                    <!-- Dynamic rendering by drawQuestion() -->
                </div>

                <!-- Right Side: Sidebar Controls & Number Grid -->
                <div class="quiz-sidebar">
                    <!-- Timer -->
                    <div class="timer-panel" id="timer-panel-el">
                        <div class="timer-title"><i class="fa-regular fa-clock"></i> الوقت المتبقي</div>
                        <div class="timer-value" id="timer-val-el">--:--</div>
                    </div>

                    <!-- Question Status Grid -->
                    <div class="flag-panel">
                        <div class="flag-grid-title">شبكة الأسئلة</div>
                        <div class="flag-grid" id="flag-buttons-grid">
                            <!-- Numbered buttons loaded dynamically -->
                        </div>
                        
                        <!-- Color status legends -->
                        <div class="flag-legend">
                            <div class="legend-item">
                                <div class="legend-dot green"></div>
                                <span>تم الإجابة</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-dot gray"></div>
                                <span>لم يُجب / تجاوز</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-dot white"></div>
                                <span>مُعلَّم للمراجعة</span>
                            </div>
                        </div>
                    </div>

                    <!-- Submit Button -->
                    <button id="submit-quiz-btn" class="btn btn-primary" style="width: 100%;">
                        <i class="fa-solid fa-cloud-arrow-up"></i> تسليم الإجابات
                    </button>
                </div>
            </div>
        `;

        updateTimerDisplay();
        drawQuestion();
        drawFlagGrid();
        bindEvents();
    }

    function drawQuestion() {
        const qCard = document.getElementById('question-card');
        const q = questions[currentQuestionIdx];
        const isFlagged = flaggedQuestions[currentQuestionIdx];
        
        qCard.innerHTML = `
            <div class="question-header">
                <span class="question-num">السؤال ${currentQuestionIdx + 1} من ${totalQuestions}</span>
                <button id="flag-btn-toggle" class="flag-action-btn ${isFlagged ? 'flagged' : ''}">
                    <i class="${isFlagged ? 'fa-solid' : 'fa-regular'} fa-flag"></i> 
                    ${isFlagged ? 'مُعلَّم' : 'تعليم للمراجعة'}
                </button>
            </div>
            
            <p class="question-text">${q.question}</p>
            
            <div class="choices-container">
                ${q.choices.map((choice, idx) => {
                    const letter = String.fromCharCode(65 + idx); // A, B, C, D
                    const isSelected = userAnswers[currentQuestionIdx] === idx;
                    return `
                        <div class="choice-option ${isSelected ? 'selected' : ''}" data-idx="${idx}">
                            <div class="choice-letter">${letter}</div>
                            <div class="choice-text">${choice}</div>
                        </div>
                    `;
                }).join('')}
            </div>
            
            <div class="quiz-navigation">
                <button id="prev-q-btn" class="btn btn-secondary" ${currentQuestionIdx === 0 ? 'disabled' : ''}>
                    <i class="fa-solid fa-arrow-right"></i> السابق
                </button>
                <button id="next-q-btn" class="btn btn-secondary" ${currentQuestionIdx === totalQuestions - 1 ? 'disabled' : ''}>
                    التالي <i class="fa-solid fa-arrow-left"></i>
                </button>
            </div>
        `;

        // Bind clicks for choice option selection
        qCard.querySelectorAll('.choice-option').forEach(option => {
            option.addEventListener('click', () => {
                const idx = parseInt(option.getAttribute('data-idx'));
                userAnswers[currentQuestionIdx] = idx;
                
                // Redraw option states and flag grid
                qCard.querySelectorAll('.choice-option').forEach(opt => opt.classList.remove('selected'));
                option.classList.add('selected');
                
                drawFlagGrid();
            });
        });

        // Bind flag toggle button click
        document.getElementById('flag-btn-toggle').addEventListener('click', () => {
            flaggedQuestions[currentQuestionIdx] = !flaggedQuestions[currentQuestionIdx];
            drawQuestion(); // Re-render local flag view state
            drawFlagGrid(); // Re-render grid layout states
        });

        // Navigation back
        document.getElementById('prev-q-btn').addEventListener('click', () => {
            if (currentQuestionIdx > 0) {
                currentQuestionIdx--;
                drawQuestion();
                drawFlagGrid();
            }
        });

        // Navigation forward
        document.getElementById('next-q-btn').addEventListener('click', () => {
            if (currentQuestionIdx < totalQuestions - 1) {
                currentQuestionIdx++;
                drawQuestion();
                drawFlagGrid();
            }
        });
    }

    function drawFlagGrid() {
        const grid = document.getElementById('flag-buttons-grid');
        if (!grid) return;

        grid.innerHTML = questions.map((q, idx) => {
            const isAnswered = userAnswers[idx] !== -1;
            const isFlagged = flaggedQuestions[idx];
            const isActive = idx === currentQuestionIdx;
            
            // Priority: Flagged (White), Answered (Green), Skipped/Unanswered (Gray)
            let colorClass = 'skipped';
            if (isFlagged) {
                colorClass = 'flagged';
            } else if (isAnswered) {
                colorClass = 'answered';
            }
            
            const activeClass = isActive ? 'active-question' : '';

            return `
                <button class="flag-btn ${colorClass} ${activeClass}" data-idx="${idx}">
                    ${idx + 1}
                </button>
            `;
        }).join('');

        // Bind grid button clicks for routing directly to question index
        grid.querySelectorAll('.flag-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                currentQuestionIdx = parseInt(btn.getAttribute('data-idx'));
                drawQuestion();
                drawFlagGrid();
            });
        });
    }

    function bindEvents() {
        // Main Submit quiz button
        document.getElementById('submit-quiz-btn').addEventListener('click', () => {
            const unansweredCount = userAnswers.filter(a => a === -1).length;
            let warningMsg = "هل أنت متأكد من تسليم إجاباتك؟";
            if (unansweredCount > 0) {
                warningMsg = `لديك ${unansweredCount} سؤال لم تُجب عنه. هل تريد التسليم؟`;
            }
            
            if (confirm(warningMsg)) {
                submitQuiz();
            }
        });
    }

    async function submitQuiz() {
        // Stop timer ticking
        clearInterval(timerInterval);
        
        // Show submitting state
        container.innerHTML = `
            <div class="loader-container" style="flex-direction: column; gap: 20px;">
                <div class="spinner"></div>
                <h3>جارٍ تصحيح إجاباتك وإعداد تقرير المراجعة...</h3>
            </div>
        `;

        const timeSpent = (time_limit * 60) - secondsRemaining;

        try {
            const result = await app.apiFetch('/api/quizzes/submit', {
                method: 'POST',
                body: JSON.stringify({
                    quiz_id: quiz_id,
                    answers: userAnswers,
                    time_spent_seconds: timeSpent
                })
            });

            app.showToast("تم تسليم الاختبار بنجاح!", "success");
            renderResults(result);
        } catch (err) {
            app.showToast("فشل تسليم الإجابات: " + err.message, 'error');
            // If failed to submit, draw back the screen
            draw();
        }
    }

    // --- Post Quiz Grading Report Screen ---
    function renderResults(result) {
        const { score, total_questions, correct_answers, time_spent_seconds, breakdown } = result;
        
        const minutes = Math.floor(time_spent_seconds / 60);
        const seconds = time_spent_seconds % 60;
        const timeStr = `${minutes}د ${seconds}ث`;

        container.innerHTML = `
            <div class="setup-container">
                <div class="card results-header">
                    <h2>تقرير تصحيح الاختبار</h2>
                    <p>${title}</p>
                    
                    <div class="score-circle">
                        <span class="score-num">${score}%</span>
                        <span class="score-label">الدرجة النهائية</span>
                    </div>
                    
                    <div style="display: flex; justify-content: center; gap: 32px; margin-top: 20px; font-weight: 500;">
                        <div>
                            <span style="color: #6b7280; font-size: 0.85rem; display: block; text-transform: uppercase;">الإجابات الصحيحة</span>
                            <span style="font-size: 1.3rem; color: var(--color-success);">${correct_answers} / ${total_questions}</span>
                        </div>
                        <div>
                            <span style="color: #6b7280; font-size: 0.85rem; display: block; text-transform: uppercase;">الوقت المستغرق</span>
                            <span style="font-size: 1.3rem; color: var(--color-info);">${timeStr}</span>
                        </div>
                    </div>
                </div>

                <div class="breakdown-list">
                    <h3 style="text-align: right; margin-bottom: 8px;"><i class="fa-solid fa-list-check"></i> تفصيل الإجابات</h3>
                    
                    ${breakdown.map((item, idx) => {
                        const isCorrect = item.is_correct;
                        const statusClass = isCorrect ? 'correct' : 'incorrect';
                        
                        return `
                            <div class="breakdown-card ${statusClass}">
                                <div class="breakdown-q-title">
                                    <span style="color: ${isCorrect ? 'var(--color-success)' : 'var(--color-danger)'}; font-weight: 700;">
                                        ${idx + 1}. ${isCorrect ? '<i class="fa-solid fa-circle-check"></i>' : '<i class="fa-solid fa-circle-xmark"></i>'}
                                    </span>
                                    ${item.question}
                                </div>
                                
                                <div class="breakdown-choices">
                                    ${item.choices.map((choice, cIdx) => {
                                        const letter = String.fromCharCode(65 + cIdx);
                                        
                                        // Styling rules for results options
                                        let optionClass = '';
                                        if (item.user_answer === cIdx) {
                                            optionClass = isCorrect ? 'user-correct' : 'user-incorrect';
                                        } else if (item.correct_answer === cIdx) {
                                            optionClass = 'actual-correct';
                                        }
                                        
                                        return `
                                            <div class="bd-choice ${optionClass}">
                                                <strong>${letter}:</strong> ${choice}
                                            </div>
                                        `;
                                    }).join('')}
                                </div>
                                
                                <div class="explanation-box">
                                    <strong>التفسير:</strong> ${item.explanation || "لا يوجد تفسير متاح."}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>

                <div style="margin-top: 32px; display: flex; gap: 16px;">
                    <button id="back-dash-btn" class="btn btn-primary" style="flex: 1;">
                        <i class="fa-solid fa-house-chimney"></i> العودة للوحة التحكم
                    </button>
                    <button id="retry-btn" class="btn btn-secondary" style="flex: 1;">
                        <i class="fa-solid fa-rotate-right"></i> اختبار آخر
                    </button>
                </div>
            </div>
        `;

        document.getElementById('back-dash-btn').addEventListener('click', () => {
            app.navigateTo('dashboard');
        });

        document.getElementById('retry-btn').addEventListener('click', () => {
            app.navigateTo('quiz-setup');
        });
    }

    draw();
}
