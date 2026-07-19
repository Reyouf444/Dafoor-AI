/* ==========================================================================
   Dafoor AI - Active Quiz & Review Component (Vanilla JS)
   ========================================================================== */

export function renderQuizActive(container, app, quizData) {
    if (!quizData) {
        app.showToast("No active quiz session found.", 'error');
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
                app.showToast("Time's up! Submitting your answers automatically...", 'warning');
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
                        <div class="timer-title"><i class="fa-regular fa-clock"></i> Time Remaining</div>
                        <div class="timer-value" id="timer-val-el">--:--</div>
                    </div>

                    <!-- Question Status Grid -->
                    <div class="flag-panel">
                        <div class="flag-grid-title">Question Grid</div>
                        <div class="flag-grid" id="flag-buttons-grid">
                            <!-- Numbered buttons loaded dynamically -->
                        </div>
                        
                        <!-- Color status legends -->
                        <div class="flag-legend">
                            <div class="legend-item">
                                <div class="legend-dot green"></div>
                                <span>Answered</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-dot gray"></div>
                                <span>Skipped / Unanswered</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-dot white"></div>
                                <span>Flagged for Review</span>
                            </div>
                        </div>
                    </div>

                    <!-- Submit Button -->
                    <button id="submit-quiz-btn" class="btn btn-primary" style="width: 100%;">
                        <i class="fa-solid fa-cloud-arrow-up"></i> Submit Answers
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
        const qtype = q.type || 'mcq';
        const userAns = userAnswers[currentQuestionIdx];
        
        let choicesHtml = '';

        if (qtype === 'fillblank') {
            const currentVal = (userAns !== -1 && userAns !== undefined && userAns !== null) ? userAns : '';
            choicesHtml = `
                <div class="fillblank-container" style="margin: 20px 0;">
                    <label style="display:block; font-size:0.9rem; color:#9ca3af; margin-bottom:8px;">
                        Type your answer (exact match):
                    </label>
                    <input 
                        type="text" 
                        id="fillblank-input" 
                        class="form-input" 
                        placeholder="Type answer here..." 
                        value="${currentVal}"
                        style="font-size: 1.1rem; padding: 14px; background: rgba(255,255,255,0.05); border: 2px solid var(--color-border); border-radius: 12px; color: #fff; width: 100%; transition: border-color 0.2s;"
                    />
                </div>
            `;
        } else {
            // MCQ or True/False choices
            const choicesList = q.choices && q.choices.length ? q.choices : (qtype === 'truefalse' ? ['True', 'False'] : []);
            choicesHtml = `
                <div class="choices-container">
                    ${choicesList.map((choice, idx) => {
                        const letter = String.fromCharCode(65 + idx); // A, B, C, D
                        const isSelected = userAns === idx;
                        return `
                            <div class="choice-option ${isSelected ? 'selected' : ''}" data-idx="${idx}">
                                <div class="choice-letter">${letter}</div>
                                <div class="choice-text">${choice}</div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        qCard.innerHTML = `
            <div class="question-header">
                <span class="question-num">Question ${currentQuestionIdx + 1} of ${totalQuestions} <span style="font-size:0.75rem; background:rgba(255,255,255,0.1); padding:2px 8px; border-radius:10px; margin-left:8px; text-transform:uppercase;">${qtype}</span></span>
                <button id="flag-btn-toggle" class="flag-action-btn ${isFlagged ? 'flagged' : ''}">
                    <i class="${isFlagged ? 'fa-solid' : 'fa-regular'} fa-flag"></i> 
                    ${isFlagged ? 'Flagged' : 'Flag Question'}
                </button>
            </div>
            
            <p class="question-text">${q.question}</p>
            
            ${choicesHtml}
            
            <div class="quiz-navigation">
                <button id="prev-q-btn" class="btn btn-secondary" ${currentQuestionIdx === 0 ? 'disabled' : ''}>
                    <i class="fa-solid fa-arrow-left"></i> Previous
                </button>
                <button id="next-q-btn" class="btn btn-secondary" ${currentQuestionIdx === totalQuestions - 1 ? 'disabled' : ''}>
                    Next <i class="fa-solid fa-arrow-right"></i>
                </button>
            </div>
        `;

        if (qtype === 'fillblank') {
            const inputEl = document.getElementById('fillblank-input');
            inputEl.addEventListener('input', () => {
                const text = inputEl.value.trim();
                userAnswers[currentQuestionIdx] = text !== '' ? text : -1;
                drawFlagGrid();
            });
        } else {
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
        }

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
            let warningMsg = "Are you sure you want to submit your answers?";
            if (unansweredCount > 0) {
                warningMsg = `You have ${unansweredCount} unanswered questions. Are you sure you want to submit?`;
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
                <h3>Grading your answers and generating review guide...</h3>
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

            app.showToast("Quiz submitted successfully!", "success");
            renderResults(result);
        } catch (err) {
            app.showToast("Failed to submit answers: " + err.message, 'error');
            // If failed to submit, draw back the screen
            draw();
        }
    }

    // --- Post Quiz Grading Report Screen ---
    function renderResults(result) {
        const { score, total_questions, correct_answers, time_spent_seconds, breakdown } = result;
        
        const minutes = Math.floor(time_spent_seconds / 60);
        const seconds = time_spent_seconds % 60;
        const timeStr = `${minutes}m ${seconds}s`;

        container.innerHTML = `
            <div class="setup-container">
                <div class="card results-header">
                    <h2>Quiz Grading Report</h2>
                    <p>${title}</p>
                    
                    <div class="score-circle">
                        <span class="score-num">${score}%</span>
                        <span class="score-label">Final Score</span>
                    </div>
                    
                    <div style="display: flex; justify-content: center; gap: 32px; margin-top: 20px; font-weight: 500;">
                        <div>
                            <span style="color: #6b7280; font-size: 0.85rem; display: block; text-transform: uppercase;">Correct</span>
                            <span style="font-size: 1.3rem; color: var(--color-success);">${correct_answers} / ${total_questions}</span>
                        </div>
                        <div>
                            <span style="color: #6b7280; font-size: 0.85rem; display: block; text-transform: uppercase;">Time Taken</span>
                            <span style="font-size: 1.3rem; color: var(--color-info);">${timeStr}</span>
                        </div>
                    </div>
                </div>

                <div class="breakdown-list">
                    <h3 style="text-align: left; margin-bottom: 8px;"><i class="fa-solid fa-list-check"></i> Answer Breakdown</h3>
                    
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
                                    <strong>Explanation:</strong> ${item.explanation || "No explanation provided."}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>

                <div style="margin-top: 32px; display: flex; gap: 16px;">
                    <button id="back-dash-btn" class="btn btn-primary" style="flex: 1;">
                        <i class="fa-solid fa-house-chimney"></i> Back to Dashboard
                    </button>
                    <button id="retry-btn" class="btn btn-secondary" style="flex: 1;">
                        <i class="fa-solid fa-rotate-right"></i> Try Another Quiz
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
