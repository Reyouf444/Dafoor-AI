/* ==========================================================================
   Dafoor AI - User Settings Page Component (Vanilla JS)

   Sections:
     1. Profile — display name, email, username (read-only)
     2. Security — change password, linked accounts
     3. Danger Zone — delete account
   ========================================================================== */

export function renderSettings(container, app) {

    async function draw() {
        container.innerHTML = '<div class="loader-container"><div class="spinner"></div></div>';

        try {
            const settings = await app.apiFetch('/api/user/settings');
            renderSettingsPage(settings);
        } catch (err) {
            container.innerHTML = `
                <div class="card" style="text-align: center;">
                    <h2>Error Loading Settings</h2>
                    <p style="margin: 16px 0;">${err.message}</p>
                    <button class="btn btn-primary" onclick="window.location.reload()">Retry</button>
                </div>
            `;
        }
    }

    function renderSettingsPage(settings) {
        const memberSince = settings.created_at 
            ? new Date(settings.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
            : 'Unknown';

        container.innerHTML = `
            <div class="settings-page">
                <div class="settings-header">
                    <h1><i class="fa-solid fa-gear"></i> Settings</h1>
                    <p>Manage your account, profile, and security preferences.</p>
                </div>

                <!-- Profile Section -->
                <div class="card settings-card">
                    <h3 class="settings-section-title">
                        <i class="fa-regular fa-circle-user"></i> Profile
                    </h3>
                    
                    <div class="settings-field">
                        <label class="form-label">Username</label>
                        <div class="settings-value-static">
                            <i class="fa-solid fa-at" style="color: #6b7280;"></i>
                            <span>${settings.username}</span>
                            <span class="badge">${settings.auth_provider === 'google' ? 'Google Account' : 'Local Account'}</span>
                        </div>
                    </div>

                    <form id="profile-form">
                        <div class="form-group">
                            <label class="form-label" for="settings-display-name">Display Name</label>
                            <input 
                                type="text" 
                                id="settings-display-name" 
                                class="form-input" 
                                value="${settings.display_name || ''}"
                                placeholder="Your display name"
                            />
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="settings-email">
                                Email
                                <span style="color: #6b7280; font-weight: 400; font-size: 0.85rem;"> — used for password recovery</span>
                            </label>
                            <input 
                                type="email" 
                                id="settings-email" 
                                class="form-input" 
                                value="${settings.email || ''}"
                                placeholder="you@example.com"
                            />
                        </div>
                        <button type="submit" id="save-profile-btn" class="btn btn-primary">
                            <i class="fa-solid fa-floppy-disk"></i> Save Changes
                        </button>
                    </form>

                    <div class="settings-meta">
                        <span><i class="fa-regular fa-calendar"></i> Member since ${memberSince}</span>
                    </div>
                </div>

                <!-- Security Section -->
                <div class="card settings-card">
                    <h3 class="settings-section-title">
                        <i class="fa-solid fa-shield-halved"></i> Security
                    </h3>

                    ${settings.has_password ? `
                    <form id="password-form">
                        <div class="form-group">
                            <label class="form-label" for="current-password">Current Password</label>
                            <input 
                                type="password" 
                                id="current-password" 
                                class="form-input" 
                                placeholder="••••••••" 
                                required
                                autocomplete="current-password"
                            />
                        </div>
                        <div class="settings-field-row">
                            <div class="form-group" style="flex: 1;">
                                <label class="form-label" for="new-password">New Password</label>
                                <input 
                                    type="password" 
                                    id="new-password" 
                                    class="form-input" 
                                    placeholder="••••••••" 
                                    required
                                    minlength="6"
                                    autocomplete="new-password"
                                />
                            </div>
                            <div class="form-group" style="flex: 1;">
                                <label class="form-label" for="confirm-new-password">Confirm New Password</label>
                                <input 
                                    type="password" 
                                    id="confirm-new-password" 
                                    class="form-input" 
                                    placeholder="••••••••" 
                                    required
                                    minlength="6"
                                    autocomplete="new-password"
                                />
                            </div>
                        </div>
                        <button type="submit" id="change-password-btn" class="btn btn-secondary">
                            <i class="fa-solid fa-key"></i> Change Password
                        </button>
                    </form>
                    ` : `
                    <div class="settings-info-box">
                        <i class="fa-solid fa-info-circle"></i>
                        <span>You signed up with Google — no password is set. You can continue using Google to sign in.</span>
                    </div>
                    `}

                    <!-- Linked Accounts -->
                    <div class="linked-accounts">
                        <h4 style="margin-bottom: 12px; font-size: 0.95rem; color: #d1d5db;">Linked Accounts</h4>
                        <div class="linked-account-item ${settings.has_google ? 'connected' : ''}">
                            <div class="linked-account-info">
                                <svg width="20" height="20" viewBox="0 0 48 48">
                                    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                                    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                                    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                                    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                                </svg>
                                <span>Google</span>
                            </div>
                            <span class="linked-status ${settings.has_google ? 'connected' : ''}">
                                ${settings.has_google 
                                    ? '<i class="fa-solid fa-circle-check"></i> Connected' 
                                    : '<i class="fa-regular fa-circle"></i> Not connected'}
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Danger Zone -->
                <div class="card settings-card danger-zone-card">
                    <h3 class="settings-section-title danger">
                        <i class="fa-solid fa-triangle-exclamation"></i> Danger Zone
                    </h3>
                    <p style="margin-bottom: 16px; font-size: 0.95rem;">
                        Permanently delete your account and all associated data. This action cannot be undone.
                    </p>
                    <button id="delete-account-btn" class="btn btn-danger">
                        <i class="fa-solid fa-trash"></i> Delete My Account
                    </button>
                </div>

                <!-- Delete Confirmation Modal -->
                <div id="delete-confirm-overlay" class="modal-overlay" style="display: none;">
                    <div class="modal-content card">
                        <div class="modal-header">
                            <h3 style="color: var(--color-danger);"><i class="fa-solid fa-triangle-exclamation"></i> Confirm Account Deletion</h3>
                        </div>
                        <p style="margin: 16px 0; font-size: 0.95rem;">
                            This will <strong style="color: var(--color-danger);">permanently delete</strong> your account, all uploaded PDFs, quizzes, and analytics data. This cannot be reversed.
                        </p>
                        <p style="margin-bottom: 20px; font-size: 0.9rem;">
                            Type <strong style="color: #ffffff;">DELETE</strong> to confirm:
                        </p>
                        <div class="form-group">
                            <input type="text" id="delete-confirm-input" class="form-input" placeholder='Type "DELETE" here' />
                        </div>
                        <div style="display: flex; gap: 12px; justify-content: flex-end;">
                            <button id="cancel-delete-btn" class="btn btn-secondary">Cancel</button>
                            <button id="confirm-delete-btn" class="btn btn-danger" disabled>
                                <i class="fa-solid fa-trash"></i> Delete Forever
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        bindSettingsEvents(settings);
    }

    function bindSettingsEvents(settings) {
        // ── Profile form ──
        const profileForm = document.getElementById('profile-form');
        if (profileForm) {
            profileForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const btn = document.getElementById('save-profile-btn');
                const displayName = document.getElementById('settings-display-name').value.trim();
                const email = document.getElementById('settings-email').value.trim();

                btn.disabled = true;
                btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Saving...';

                try {
                    await app.apiFetch('/api/user/settings', {
                        method: 'PUT',
                        body: JSON.stringify({
                            display_name: displayName || null,
                            email: email || null,
                        })
                    });
                    app.showToast('Profile updated successfully!', 'success');
                } catch (err) {
                    app.showToast(err.message, 'error');
                }

                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Changes';
            });
        }

        // ── Change password form ──
        const passwordForm = document.getElementById('password-form');
        if (passwordForm) {
            passwordForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const btn = document.getElementById('change-password-btn');
                const currentPwd = document.getElementById('current-password').value;
                const newPwd = document.getElementById('new-password').value;
                const confirmPwd = document.getElementById('confirm-new-password').value;

                if (newPwd !== confirmPwd) {
                    app.showToast('New passwords do not match', 'error');
                    return;
                }

                btn.disabled = true;
                btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Changing...';

                try {
                    await app.apiFetch('/api/user/password', {
                        method: 'PUT',
                        body: JSON.stringify({
                            current_password: currentPwd,
                            new_password: newPwd,
                        })
                    });
                    app.showToast('Password changed successfully!', 'success');
                    passwordForm.reset();
                } catch (err) {
                    app.showToast(err.message, 'error');
                }

                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-key"></i> Change Password';
            });
        }

        // ── Delete account ──
        const deleteBtn = document.getElementById('delete-account-btn');
        const deleteOverlay = document.getElementById('delete-confirm-overlay');
        const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
        const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
        const confirmInput = document.getElementById('delete-confirm-input');

        deleteBtn.addEventListener('click', () => {
            deleteOverlay.style.display = 'flex';
            requestAnimationFrame(() => deleteOverlay.classList.add('visible'));
        });

        cancelDeleteBtn.addEventListener('click', () => {
            deleteOverlay.classList.remove('visible');
            setTimeout(() => {
                deleteOverlay.style.display = 'none';
                confirmInput.value = '';
                confirmDeleteBtn.disabled = true;
            }, 300);
        });

        confirmInput.addEventListener('input', () => {
            confirmDeleteBtn.disabled = confirmInput.value.trim() !== 'DELETE';
        });

        confirmDeleteBtn.addEventListener('click', async () => {
            confirmDeleteBtn.disabled = true;
            confirmDeleteBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Deleting...';

            try {
                await app.apiFetch('/api/user/account', { method: 'DELETE' });
                app.showToast('Account deleted. Goodbye!', 'success');
                app.logout();
            } catch (err) {
                app.showToast(err.message, 'error');
                confirmDeleteBtn.disabled = false;
                confirmDeleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i> Delete Forever';
            }
        });
    }

    draw();
}
