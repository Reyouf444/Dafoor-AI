/* ==========================================================================
   Dafoor AI - Live Quiz Multiplayer Component (Vanilla JS)
   Real-time multi-user quiz host/guest lobby & game loop via polling.
   ========================================================================== */

export async function renderLiveQuiz(container, app, routeParams) {
    let roomCode = routeParams ? (routeParams.code || null) : null;
    let roomState = null;
    let pollInterval = null;

    let userQuizzes = [];
    let selectedQuizId = null;

    // Load available quizzes for host mode
    try {
        const history = await app.apiFetch('/api/quizzes/history');
        userQuizzes = history.quizzes || [];
        if (userQuizzes.length > 0) selectedQuizId = userQuizzes[0].id;
    } catch (err) {
        console.warn("Could not load user quizzes:", err);
    }

    if (roomCode) {
        startPolling(roomCode);
    } else {
        drawLanding();
    }

    function startPolling(code) {
        roomCode = code.toUpperCase();
        if (pollInterval) clearInterval(pollInterval);

        fetchState();
        pollInterval = setInterval(fetchState, 1500); // 1.5s live sync
    }

    async function fetchState() {
        if (!roomCode) return;
        try {
            roomState = await app.apiFetch(`/api/rooms/${roomCode}/state`);
            drawRoom();
        } catch (err) {
            console.error("Room sync error:", err);
            if (pollInterval) clearInterval(pollInterval);
            app.showToast("Room closed or expired", 'error');
            roomCode = null;
            roomState = null;
            drawLanding();
        }
    }

    function drawLanding() {
        if (pollInterval) clearInterval(pollInterval);

        container.innerHTML = `
            <div class="card" style="max-width: 650px; margin: 20px auto; padding: 30px;">
                <div style="text-align: center; margin-bottom: 24px;">
                    <div style="font-size: 2.5rem; margin-bottom: 8px;">⚔️</div>
                    <h2 style="color: #fff; margin-bottom: 6px;">Live Multiplayer Quiz</h2>
                    <p style="color: #9ca3af; font-size: 0.9rem;">Host a live session or join a room with friends!</p>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                    
                    <!-- Join Room Card -->
                    <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--color-border); border-radius: 16px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <h3 style="color: #fff; font-size: 1rem; margin-bottom: 8px;"><i class="fa-solid fa-right-to-bracket" style="color: var(--color-primary-light);"></i> Join a Room</h3>
                            <p style="color: #6b7280; font-size: 0.8rem; margin-bottom: 16px;">Enter the 6-character room code from your host.</p>
                            
                            <input type="text" id="join-code-input" class="form-input" placeholder="e.g. A3F8C2" maxlength="6" style="text-transform: uppercase; font-size: 1.2rem; letter-spacing: 3px; text-align: center; font-weight: 700; font-family: monospace; margin-bottom: 12px;" />
                        </div>
                        <button id="join-room-btn" class="btn btn-primary" style="width: 100%;">
                            Join Session
                        </button>
                    </div>

                    <!-- Host Room Card -->
                    <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--color-border); border-radius: 16px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <h3 style="color: #fff; font-size: 1rem; margin-bottom: 8px;"><i class="fa-solid fa-crown" style="color: #f59e0b;"></i> Host New Room</h3>
                            <p style="color: #6b7280; font-size: 0.8rem; margin-bottom: 16px;">Select one of your generated quizzes to host live.</p>
                            
                            <select id="host-quiz-select" class="form-input" style="font-size: 0.85rem; margin-bottom: 12px;">
                                ${userQuizzes.length > 0 ? '' : '<option value="">No quizzes generated yet</option>'}
                                ${userQuizzes.map(q => `<option value="${q.id}">${q.title}</option>`).join('')}
                            </select>
                        </div>
                        <button id="create-room-btn" class="btn btn-primary" ${userQuizzes.length === 0 ? 'disabled' : ''} style="width: 100%;">
                            Create Room
                        </button>
                    </div>

                </div>
            </div>
        `;

        // Join click
        document.getElementById('join-room-btn').addEventListener('click', async () => {
            const input = document.getElementById('join-code-input');
            const code = input.value.trim().toUpperCase();
            if (!code || code.length !== 6) {
                app.showToast("Enter a valid 6-character room code", 'warning');
                return;
            }

            try {
                await app.apiFetch(`/api/rooms/${code}/join`, {
                    method: 'POST',
                    body: JSON.stringify({})
                });
                startPolling(code);
            } catch (err) {
                app.showToast("Could not join room: " + err.message, 'error');
            }
        });

        // Create click
        const createBtn = document.getElementById('create-room-btn');
        if (createBtn) {
            createBtn.addEventListener('click', async () => {
                const select = document.getElementById('host-quiz-select');
                const quizId = select ? select.value : null;
                if (!quizId) {
                    app.showToast("Generate a quiz first from Quiz Setup!", 'warning');
                    return;
                }

                try {
                    const res = await app.apiFetch('/api/rooms/create', {
                        method: 'POST',
                        body: JSON.stringify({ quiz_id: quizId, time_limit_per_q: 20 })
                    });
                    startPolling(res.code);
                } catch (err) {
                    app.showToast("Failed to create room: " + err.message, 'error');
                }
            });
        }
    }

    function drawRoom() {
        if (!roomState) return;

        const { status, code, host_username, participant_list, answered_count, total_players, current_q_idx, total_questions, is_host, question, seconds_remaining, time_limit } = roomState;

        if (status === 'lobby') {
            renderLobby(code, host_username, participant_list, is_host);
        } else if (status === 'question' || status === 'reveal') {
            renderGameQuestion(roomState);
        } else if (status === 'ended') {
            renderLeaderboard(roomState);
        }
    }

    function renderLobby(code, hostUsername, players, isHost) {
        container.innerHTML = `
            <div class="card" style="max-width: 600px; margin: 20px auto; padding: 30px; text-align: center;">
                <div style="background: rgba(124, 58, 237, 0.15); border: 2px dashed var(--color-primary); border-radius: 16px; padding: 20px; margin-bottom: 24px;">
                    <div style="font-size: 0.85rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">ROOM CODE</div>
                    <div style="font-size: 3rem; font-weight: 800; color: #fff; font-family: monospace; letter-spacing: 6px;">${code}</div>
                    <div style="font-size: 0.8rem; color: #a78bfa; margin-top: 4px;">Share this code with players to join!</div>
                </div>

                <h3 style="color: #fff; margin-bottom: 12px; font-size: 1.1rem;">Players in Lobby (${players.length})</h3>
                
                <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-bottom: 30px; min-height: 80px; align-content: flex-start;">
                    ${players.map(p => `
                        <div style="background: rgba(255,255,255,0.06); border: 1px solid var(--color-border); padding: 8px 16px; border-radius: 20px; color: #fff; font-size: 0.9rem; display: flex; align-items: center; gap: 8px;">
                            <i class="fa-solid fa-user-astronaut" style="color: var(--color-primary-light);"></i>
                            ${p.username} ${p.is_host ? '<span style="font-size:0.7rem; background:#f59e0b; color:#000; padding:1px 6px; border-radius:10px; font-weight:bold;">HOST</span>' : ''}
                        </div>
                    `).join('')}
                </div>

                ${isHost ? `
                    <button id="start-game-btn" class="btn btn-primary" style="width: 100%; font-size: 1.1rem; padding: 14px;">
                        <i class="fa-solid fa-play"></i> Start Quiz Now
                    </button>
                ` : `
                    <div style="color: #9ca3af; font-size: 0.9rem;">
                        <i class="fa-solid fa-circle-notch fa-spin"></i> Waiting for host (<strong>${hostUsername}</strong>) to start...
                    </div>
                `}
            </div>
        `;

        const startBtn = document.getElementById('start-game-btn');
        if (startBtn) {
            startBtn.addEventListener('click', async () => {
                try {
                    await app.apiFetch(`/api/rooms/${code}/start`, { method: 'POST' });
                    fetchState();
                } catch (err) {
                    app.showToast("Could not start quiz: " + err.message, 'error');
                }
            });
        }
    }

    function renderGameQuestion(state) {
        const { code, status, question, current_q_idx, total_questions, seconds_remaining, time_limit, answered_count, total_players, is_host, correct_index, correct_answer_text, my_answer, participant_list } = state;
        const qtype = question ? question.type : 'mcq';

        const isReveal = (status === 'reveal');

        container.innerHTML = `
            <div style="max-width: 800px; margin: 0 auto;">
                
                <!-- Live Header & Countdown -->
                <div class="card" style="margin-bottom: 20px; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <span style="font-size: 0.85rem; color: #9ca3af;">Question ${current_q_idx + 1} of ${total_questions}</span>
                        <h4 style="color: #fff; margin: 0; font-size: 1rem;">Room: ${code}</h4>
                    </div>

                    <!-- Per-Question Countdown bar -->
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <div style="text-align: right;">
                            <div style="font-size: 0.75rem; color: #9ca3af;">TIME LEFT</div>
                            <div style="font-size: 1.4rem; font-weight: 700; color: ${seconds_remaining <= 5 ? 'var(--color-danger)' : '#fff'};">
                                ${Math.ceil(seconds_remaining)}s
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 0.75rem; color: #9ca3af;">ANSWERS</div>
                            <div style="font-size: 1.2rem; font-weight: 600; color: var(--color-primary-light);">
                                ${answered_count} / ${total_players}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Main Question Card -->
                <div class="card" style="margin-bottom: 20px; padding: 30px;">
                    <p style="color: #fff; font-size: 1.2rem; font-weight: 500; margin-bottom: 24px; line-height: 1.5;">
                        ${question ? question.question : ''}
                    </p>

                    ${renderQuestionInput(state)}
                </div>

                <!-- Live Scoreboard preview & Host Next controls -->
                <div class="card" style="padding: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h4 style="color: #fff; font-size: 0.95rem; margin: 0;">Live Leaderboard</h4>
                        ${is_host && isReveal ? `
                            <button id="next-room-q-btn" class="btn btn-primary">
                                ${current_q_idx + 1 >= total_questions ? 'Finish Quiz <i class="fa-solid fa-trophy"></i>' : 'Next Question <i class="fa-solid fa-arrow-right"></i>'}
                            </button>
                        ` : ''}
                    </div>

                    <div style="display: flex; gap: 12px; overflow-x: auto; padding-bottom: 4px;">
                        ${participant_list.map((p, rank) => `
                            <div style="background: rgba(255,255,255,0.05); border: 1px solid var(--color-border); border-radius: 12px; padding: 10px 16px; min-width: 130px; text-align: center;">
                                <div style="font-size: 0.75rem; color: #9ca3af;">#${rank + 1} ${p.username}</div>
                                <div style="font-size: 1.1rem; font-weight: 700; color: #fff; margin-top: 2px;">${p.score} pts</div>
                                ${p.answered ? '<span style="font-size:0.7rem; color:#10b981;">✓ Answered</span>' : '<span style="font-size:0.7rem; color:#6b7280;">Thinking...</span>'}
                            </div>
                        `).join('')}
                    </div>
                </div>

            </div>
        `;

        bindGameEvents(state);
    }

    function renderQuestionInput(state) {
        const { status, question, my_answer, correct_index, correct_answer_text } = state;
        const qtype = question ? question.type : 'mcq';
        const isReveal = (status === 'reveal');

        if (qtype === 'fillblank') {
            return `
                <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px;">
                    <input 
                        type="text" 
                        id="live-fillblank-input" 
                        class="form-input" 
                        placeholder="Type answer here..." 
                        value="${my_answer || ''}"
                        ${isReveal || my_answer ? 'disabled' : ''}
                        style="flex: 1; font-size: 1.1rem; padding: 12px 16px;"
                    />
                    ${!isReveal && !my_answer ? `
                        <button id="live-submit-ans-btn" class="btn btn-primary">Submit</button>
                    ` : ''}
                </div>
                ${isReveal ? `
                    <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; padding: 12px; border-radius: 10px; color: #10b981; font-weight: 600;">
                        Correct Answer: ${correct_answer_text}
                    </div>
                ` : ''}
            `;
        } else {
            // MCQ or True/False choices
            const choices = question.choices && question.choices.length ? question.choices : ['True', 'False'];
            return `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    ${choices.map((choice, idx) => {
                        let btnStyle = "background: rgba(255,255,255,0.05); border: 1px solid var(--color-border); color: #fff;";
                        
                        if (isReveal) {
                            if (idx === correct_index) {
                                btnStyle = "background: rgba(16, 185, 129, 0.3); border: 2px solid #10b981; color: #fff; font-weight: bold;";
                            } else if (my_answer == idx) {
                                btnStyle = "background: rgba(239, 68, 68, 0.3); border: 2px solid #ef4444; color: #fff;";
                            }
                        } else if (my_answer == idx) {
                            btnStyle = "background: var(--color-primary); border: 1px solid var(--color-primary); color: #fff; font-weight: bold;";
                        }

                        return `
                            <button 
                                class="live-choice-btn" 
                                data-idx="${idx}"
                                ${isReveal || my_answer !== null && my_answer !== undefined ? 'disabled' : ''}
                                style="padding: 16px; border-radius: 12px; font-size: 1rem; cursor: pointer; text-align: left; transition: all 0.2s; ${btnStyle}"
                            >
                                <span style="font-weight: 700; margin-right: 8px;">${String.fromCharCode(65 + idx)}.</span> ${choice}
                            </button>
                        `;
                    }).join('')}
                </div>
            `;
        }
    }

    function bindGameEvents(state) {
        const { code, status, is_host, my_answer } = state;

        // Submit Fill-in-blank
        const fillInput = document.getElementById('live-fillblank-input');
        const submitAnsBtn = document.getElementById('live-submit-ans-btn');

        if (submitAnsBtn && fillInput) {
            submitAnsBtn.addEventListener('click', async () => {
                const ans = fillInput.value.trim();
                if (!ans) return;
                try {
                    await app.apiFetch(`/api/rooms/${code}/answer`, {
                        method: 'POST',
                        body: JSON.stringify({ answer: ans })
                    });
                    fetchState();
                } catch (err) {
                    app.showToast("Answer submit failed: " + err.message, 'error');
                }
            });
        }

        // Submit Choice (MCQ / TrueFalse)
        container.querySelectorAll('.live-choice-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const idx = parseInt(btn.getAttribute('data-idx'));
                try {
                    await app.apiFetch(`/api/rooms/${code}/answer`, {
                        method: 'POST',
                        body: JSON.stringify({ answer: idx })
                    });
                    fetchState();
                } catch (err) {
                    app.showToast("Answer submit failed: " + err.message, 'error');
                }
            });
        });

        // Host Next Question button
        const nextBtn = document.getElementById('next-room-q-btn');
        if (nextBtn) {
            nextBtn.addEventListener('click', async () => {
                try {
                    await app.apiFetch(`/api/rooms/${code}/next`, { method: 'POST' });
                    fetchState();
                } catch (err) {
                    app.showToast("Could not advance: " + err.message, 'error');
                }
            });
        }
    }

    function renderLeaderboard(state) {
        if (pollInterval) clearInterval(pollInterval);
        const { participant_list } = state;

        container.innerHTML = `
            <div class="card" style="max-width: 600px; margin: 30px auto; padding: 40px; text-align: center;">
                <div style="font-size: 3.5rem; margin-bottom: 12px;">🏆</div>
                <h2 style="color: #fff; margin-bottom: 8px;">Quiz Completed!</h2>
                <p style="color: #9ca3af; margin-bottom: 24px;">Final Standings & Leaderboard</p>

                <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 30px;">
                    ${participant_list.map((p, rank) => `
                        <div style="background: ${rank === 0 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(255,255,255,0.05)'}; border: 1px solid ${rank === 0 ? '#f59e0b' : 'var(--color-border)'}; border-radius: 12px; padding: 14px 20px; display: flex; justify-content: space-between; align-items: center;">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <span style="font-weight: 800; font-size: 1.2rem; color: ${rank === 0 ? '#f59e0b' : '#9ca3af'};">#${rank + 1}</span>
                                <span style="color: #fff; font-weight: 600; font-size: 1rem;">${p.username}</span>
                            </div>
                            <span style="color: #fff; font-weight: 700; font-size: 1.1rem;">${p.score} pts</span>
                        </div>
                    `).join('')}
                </div>

                <button id="exit-live-btn" class="btn btn-primary" style="width: 100%;">
                    Back to Dashboard
                </button>
            </div>
        `;

        document.getElementById('exit-live-btn').addEventListener('click', () => {
            app.navigateTo('dashboard');
        });
    }
}
