/* ==========================================================================
   Dafoor AI - Flashcards Component (Vanilla JS)
   Supports generating, saving, listing decks, and 3D card flipping.
   ========================================================================== */

export async function renderFlashcards(container, app) {
    let decks = [];
    let activeDeck = null;
    let currentCardIdx = 0;
    let isFlipped = false;
    let pdfs = app.state.pdfs || [];

    // Load saved decks and PDFs
    try {
        decks = await app.apiFetch('/api/flashcards');
        if (pdfs.length === 0) {
            pdfs = await app.apiFetch('/api/pdfs');
            app.state.pdfs = pdfs;
        }
    } catch (err) {
        console.error("Failed to load flashcard decks:", err);
    }

    function draw() {
        container.innerHTML = `
            <div class="flashcard-container" style="max-width: 900px; margin: 0 auto; padding: 20px;">
                
                <!-- Top Header & Creator Panel -->
                <div class="card" style="margin-bottom: 24px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                        <div>
                            <h2 style="color: #fff; margin-bottom: 4px;"><i class="fa-solid fa-layer-group" style="color: var(--color-primary);"></i> AI Flashcards</h2>
                            <p style="color: #9ca3af; font-size: 0.9rem; margin: 0;">Generate interactive 3D flashcard decks from your study PDFs</p>
                        </div>
                        
                        <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                            <select id="flash-pdf-select" class="form-input" style="width: 220px; font-size: 0.85rem;">
                                ${pdfs.length > 0 ? '' : '<option value="">No PDFs uploaded</option>'}
                                ${pdfs.map(p => `<option value="${p.id}">${p.filename}</option>`).join('')}
                            </select>
                            <button id="gen-flashcards-btn" class="btn btn-primary" ${pdfs.length === 0 ? 'disabled' : ''}>
                                <i class="fa-solid fa-wand-magic-sparkles"></i> Generate Deck
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Deck Workspace or Deck List -->
                ${activeDeck ? renderDeckViewer() : renderDeckList()}

            </div>
        `;

        bindEvents();
    }

    function renderDeckList() {
        if (decks.length === 0) {
            return `
                <div class="card" style="text-align: center; padding: 40px 20px;">
                    <i class="fa-solid fa-layer-group" style="font-size: 3rem; color: #4b5563; margin-bottom: 16px;"></i>
                    <h3 style="color: #fff; margin-bottom: 8px;">No Flashcard Decks Yet</h3>
                    <p style="color: #9ca3af; max-width: 450px; margin: 0 auto 20px;">
                        Select one of your uploaded PDFs above and click <strong>Generate Deck</strong> to automatically extract key concepts and formulas into flashcards!
                    </p>
                </div>
            `;
        }

        return `
            <div>
                <h3 style="color: #fff; margin-bottom: 16px; font-size: 1.1rem;">Saved Flashcard Decks (${decks.length})</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px;">
                    ${decks.map(d => `
                        <div class="card deck-card" data-deck-id="${d.id}" style="cursor: pointer; transition: transform 0.2s, border-color 0.2s; border: 1px solid var(--color-border);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                <div style="background: rgba(124, 58, 237, 0.2); color: var(--color-primary-light); padding: 6px 12px; border-radius: 8px; font-weight: 600; font-size: 0.8rem;">
                                    ${d.card_count || '?'} Cards
                                </div>
                                <button class="delete-deck-btn" data-deck-id="${d.id}" style="background: none; border: none; color: #6b7280; cursor: pointer; padding: 4px;" title="Delete deck">
                                    <i class="fa-solid fa-trash-can"></i>
                                </button>
                            </div>
                            <h4 style="color: #fff; margin-bottom: 6px; font-size: 1rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                ${d.title}
                            </h4>
                            <p style="color: #6b7280; font-size: 0.75rem; margin: 0;">
                                Created ${new Date(d.created_at).toLocaleDateString()}
                            </p>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    function renderDeckViewer() {
        const cards = activeDeck.cards || [];
        const card = cards[currentCardIdx] || { front: "No cards", back: "No cards" };
        const total = cards.length;

        return `
            <div>
                <!-- Navigation & Actions bar -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <button id="back-to-decks-btn" class="btn btn-secondary" style="font-size: 0.85rem;">
                        <i class="fa-solid fa-arrow-left"></i> Back to Decks
                    </button>
                    <h3 style="color: #fff; font-size: 1rem; margin: 0;">${activeDeck.title}</h3>
                    <span style="color: #9ca3af; font-size: 0.85rem;">Card ${currentCardIdx + 1} of ${total}</span>
                </div>

                <!-- 3D Flashcard container -->
                <div class="flashcard-scene" style="perspective: 1000px; width: 100%; height: 320px; margin-bottom: 24px; cursor: pointer;">
                    <div id="flashcard-3d" class="flashcard-card ${isFlipped ? 'is-flipped' : ''}" style="width: 100%; height: 100%; position: relative; transform-style: preserve-3d; transition: transform 0.6s cubic-bezier(0.4, 0.2, 0.2, 1);">
                        
                        <!-- Front side (Question / Concept) -->
                        <div class="flashcard-face flashcard-front" style="position: absolute; width: 100%; height: 100%; backface-visibility: hidden; background: linear-gradient(135deg, rgba(30,30,45,0.95), rgba(20,20,35,0.95)); border: 2px solid var(--color-border); border-radius: 20px; padding: 30px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                            <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: var(--color-primary-light); margin-bottom: 12px; font-weight: 600;">Concept / Question</div>
                            <p style="color: #fff; font-size: 1.3rem; font-weight: 500; line-height: 1.5; margin: 0; word-break: break-word;">
                                ${card.front}
                            </p>
                            <div style="margin-top: 20px; font-size: 0.8rem; color: #6b7280;">
                                <i class="fa-solid fa-rotate"></i> Click to reveal answer
                            </div>
                        </div>

                        <!-- Back side (Answer / Definition) -->
                        <div class="flashcard-face flashcard-back" style="position: absolute; width: 100%; height: 100%; backface-visibility: hidden; transform: rotateY(180deg); background: linear-gradient(135deg, rgba(45,30,60,0.95), rgba(30,20,45,0.95)); border: 2px solid var(--color-primary); border-radius: 20px; padding: 30px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; box-shadow: 0 10px 30px rgba(124,58,237,0.3);">
                            <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #a78bfa; margin-bottom: 12px; font-weight: 600;">Explanation / Answer</div>
                            <p style="color: #fff; font-size: 1.15rem; font-weight: 400; line-height: 1.5; margin: 0; word-break: break-word;">
                                ${card.back}
                            </p>
                            <div style="margin-top: 20px; font-size: 0.8rem; color: #9ca3af;">
                                <i class="fa-solid fa-rotate"></i> Click to flip back
                            </div>
                        </div>

                    </div>
                </div>

                <!-- Navigation Controls -->
                <div style="display: flex; justify-content: center; align-items: center; gap: 20px;">
                    <button id="prev-card-btn" class="btn btn-secondary" ${currentCardIdx === 0 ? 'disabled' : ''} style="width: 120px;">
                        <i class="fa-solid fa-arrow-left"></i> Previous
                    </button>

                    <button id="flip-card-btn" class="btn btn-primary" style="width: 140px;">
                        <i class="fa-solid fa-rotate"></i> ${isFlipped ? 'Show Front' : 'Show Answer'}
                    </button>

                    <button id="next-card-btn" class="btn btn-secondary" ${currentCardIdx === total - 1 ? 'disabled' : ''} style="width: 120px;">
                        Next <i class="fa-solid fa-arrow-right"></i>
                    </button>
                </div>

            </div>
        `;
    }

    function bindEvents() {
        const genBtn = document.getElementById('gen-flashcards-btn');
        const pdfSelect = document.getElementById('flash-pdf-select');

        if (genBtn) {
            genBtn.addEventListener('click', async () => {
                const pdfId = pdfSelect ? pdfSelect.value : null;
                if (!pdfId) {
                    app.showToast("Select a PDF to generate flashcards", 'warning');
                    return;
                }

                genBtn.disabled = true;
                genBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Generating...';

                try {
                    const result = await app.apiFetch('/api/flashcards/generate', {
                        method: 'POST',
                        body: JSON.stringify({
                            pdf_id: pdfId,
                            card_count: 20,
                            gemini_api_key: app.state.geminiApiKey || null
                        })
                    });

                    app.showToast("Flashcard deck generated!", 'success');
                    activeDeck = {
                        id: result.deck_id,
                        title: result.title,
                        cards: result.cards
                    };
                    currentCardIdx = 0;
                    isFlipped = false;
                    
                    // Reload decks list
                    decks = await app.apiFetch('/api/flashcards');
                    draw();
                } catch (err) {
                    app.showToast("Flashcard generation failed: " + err.message, 'error');
                    genBtn.disabled = false;
                    genBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Deck';
                }
            });
        }

        // Open deck from list
        container.querySelectorAll('.deck-card').forEach(card => {
            card.addEventListener('click', async (e) => {
                if (e.target.closest('.delete-deck-btn')) return; // ignore delete click
                const deckId = card.getAttribute('data-deck-id');
                try {
                    const deckData = await app.apiFetch(`/api/flashcards/${deckId}`);
                    let cards = deckData.cards;
                    if (typeof cards === 'string') cards = JSON.parse(cards);
                    activeDeck = { ...deckData, cards };
                    currentCardIdx = 0;
                    isFlipped = false;
                    draw();
                } catch (err) {
                    app.showToast("Failed to open deck: " + err.message, 'error');
                }
            });
        });

        // Delete deck
        container.querySelectorAll('.delete-deck-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const deckId = btn.getAttribute('data-deck-id');
                if (!confirm("Are you sure you want to delete this flashcard deck?")) return;
                try {
                    await app.apiFetch(`/api/flashcards/${deckId}`, { method: 'DELETE' });
                    app.showToast("Deck deleted", 'success');
                    decks = decks.filter(d => d.id !== deckId);
                    if (activeDeck && activeDeck.id === deckId) activeDeck = null;
                    draw();
                } catch (err) {
                    app.showToast("Failed to delete deck: " + err.message, 'error');
                }
            });
        });

        // Back to deck list
        const backBtn = document.getElementById('back-to-decks-btn');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                activeDeck = null;
                draw();
            });
        }

        // 3D Flip interactions
        const scene = container.querySelector('.flashcard-scene');
        const flipBtn = document.getElementById('flip-card-btn');

        const doFlip = () => {
            isFlipped = !isFlipped;
            const cardEl = document.getElementById('flashcard-3d');
            if (cardEl) {
                if (isFlipped) cardEl.classList.add('is-flipped');
                else cardEl.classList.remove('is-flipped');
            }
            if (flipBtn) flipBtn.innerHTML = `<i class="fa-solid fa-rotate"></i> ${isFlipped ? 'Show Front' : 'Show Answer'}`;
        };

        if (scene) scene.addEventListener('click', doFlip);
        if (flipBtn) flipBtn.addEventListener('click', doFlip);

        // Previous Card
        const prevBtn = document.getElementById('prev-card-btn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (currentCardIdx > 0) {
                    currentCardIdx--;
                    isFlipped = false;
                    draw();
                }
            });
        }

        // Next Card
        const nextBtn = document.getElementById('next-card-btn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (activeDeck && currentCardIdx < activeDeck.cards.length - 1) {
                    currentCardIdx++;
                    isFlipped = false;
                    draw();
                }
            });
        }
    }

    draw();
}
