/* ==========================================================================
   Dafoor AI - Auth Page Component (Vanilla JS)

   Features:
   - Login / Sign Up toggle
   - "Forgot your password?" flow (modal to enter email)
   - "Sign in with Google" button (Google Identity Services)
   - Email field on sign-up form (for password recovery)
   - Password reset page (accessed via #reset-password?token=xxx)
   ========================================================================== */

export function renderAuth(container, app) {
    let isLoginMode = true;
    let showForgotModal = false;
    let showResetForm = false;
    let resetToken = '';

    // Check if we're on the password reset page
    const hash = window.location.hash;
    if (hash.startsWith('#reset-password')) {
        const params = new URLSearchParams(hash.split('?')[1] || '');
        resetToken = params.get('token') || '';
        if (resetToken) {
            showResetForm = true;
        }
    }

    function draw() {
        if (showResetForm) {
            drawResetForm();
            return;
        }

        container.innerHTML = `
            <div class="auth-wrapper">
                <div class="card auth-card">
                    <!-- Dynamic Lottie Logo Animation -->
                    <div id="logo-animation" style="width: 80px; height: 80px; margin: 0 auto 16px auto;"></div>
                    <div class="auth-header">
                        <h2>${isLoginMode ? 'Welcome Back' : 'Get Started'}</h2>
                        <p>${isLoginMode ? 'Access your Dafoor AI account' : 'Create an account to start studying smarter'}</p>
                    </div>
                    
                    <form id="auth-form">
                        <div class="form-group">
                            <label class="form-label" for="username">Username</label>
                            <input 
                                type="text" 
                                id="username" 
                                class="form-input" 
                                placeholder="Enter your username" 
                                required 
                                minlength="3"
                                autocomplete="username"
                            />
                        </div>

                        ${!isLoginMode ? `
                        <div class="form-group">
                            <label class="form-label" for="email">Email <span style="color: #6b7280; font-weight: 400;">(optional — for password recovery)</span></label>
                            <input 
                                type="email" 
                                id="email" 
                                class="form-input" 
                                placeholder="you@example.com" 
                                autocomplete="email"
                            />
                        </div>
                        ` : ''}

                        <div class="form-group">
                            <label class="form-label" for="password">Password</label>
                            <input 
                                type="password" 
                                id="password" 
                                class="form-input" 
                                placeholder="••••••••" 
                                required 
                                minlength="6"
                                autocomplete="${isLoginMode ? 'current-password' : 'new-password'}"
                            />
                        </div>

                        ${isLoginMode ? `
                        <div class="forgot-password-link">
                            <a href="#" id="forgot-password-link">Forgot your password?</a>
                        </div>
                        ` : ''}
                        
                        <button type="submit" id="auth-submit-btn" class="btn btn-primary" style="width: 100%; margin-top: 10px;">
                            ${isLoginMode ? '<i class="fa-solid fa-right-to-bracket"></i> Login' : '<i class="fa-solid fa-user-plus"></i> Sign Up'}
                        </button>
                    </form>

                    <!-- OAuth Divider -->
                    <div class="auth-divider">
                        <span>or</span>
                    </div>

                    <!-- Google Sign-In Button -->
                    <button id="google-signin-btn" class="btn btn-oauth btn-google">
                        <svg width="18" height="18" viewBox="0 0 48 48">
                            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                        </svg>
                        <span>${isLoginMode ? 'Sign in with Google' : 'Sign up with Google'}</span>
                    </button>
                    
                    <div class="auth-toggle-msg">
                        <p>
                            ${isLoginMode ? "Don't have an account?" : "Already have an account?"} 
                            <a href="#" id="auth-toggle-link" style="font-weight: 600;">
                                ${isLoginMode ? 'Create one' : 'Login instead'}
                            </a>
                        </p>
                    </div>
                </div>
            </div>

            <!-- Forgot Password Modal -->
            <div id="forgot-modal-overlay" class="modal-overlay ${showForgotModal ? 'visible' : ''}" style="display: ${showForgotModal ? 'flex' : 'none'};">
                <div class="modal-content card">
                    <div class="modal-header">
                        <h3><i class="fa-solid fa-key"></i> Reset Your Password</h3>
                        <button id="close-forgot-modal" class="btn btn-icon btn-secondary">
                            <i class="fa-solid fa-xmark"></i>
                        </button>
                    </div>
                    <p style="margin-bottom: 20px; font-size: 0.95rem;">
                        Enter the email address you used when creating your account, and we'll send you a link to reset your password.
                    </p>
                    <form id="forgot-form">
                        <div class="form-group">
                            <label class="form-label" for="forgot-email">Email Address</label>
                            <input 
                                type="email" 
                                id="forgot-email" 
                                class="form-input" 
                                placeholder="you@example.com" 
                                required
                            />
                        </div>
                        <button type="submit" id="forgot-submit-btn" class="btn btn-primary" style="width: 100%;">
                            <i class="fa-solid fa-paper-plane"></i> Send Reset Link
                        </button>
                    </form>
                </div>
            </div>
        `;

        // Render Lottie Logo animation
        try {
            lottie.loadAnimation({
                container: document.getElementById('logo-animation'),
                renderer: 'svg',
                loop: true,
                autoplay: true,
                path: 'assets/dafoor_logo.json'
            });
        } catch (err) {
            console.error("Lottie player error:", err);
        }

        bindEvents();
    }

    function drawResetForm() {
        container.innerHTML = `
            <div class="auth-wrapper">
                <div class="card auth-card">
                    <div id="logo-animation" style="width: 80px; height: 80px; margin: 0 auto 16px auto;"></div>
                    <div class="auth-header">
                        <h2>Set New Password</h2>
                        <p>Choose a strong password for your Dafoor AI account.</p>
                    </div>
                    
                    <form id="reset-form">
                        <div class="form-group">
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
                        <div class="form-group">
                            <label class="form-label" for="confirm-password">Confirm Password</label>
                            <input 
                                type="password" 
                                id="confirm-password" 
                                class="form-input" 
                                placeholder="••••••••" 
                                required 
                                minlength="6"
                                autocomplete="new-password"
                            />
                        </div>
                        <button type="submit" id="reset-submit-btn" class="btn btn-primary" style="width: 100%; margin-top: 10px;">
                            <i class="fa-solid fa-check"></i> Reset Password
                        </button>
                    </form>
                    
                    <div class="auth-toggle-msg">
                        <p>
                            <a href="#" id="back-to-login">← Back to Login</a>
                        </p>
                    </div>
                </div>
            </div>
        `;

        try {
            lottie.loadAnimation({
                container: document.getElementById('logo-animation'),
                renderer: 'svg',
                loop: true,
                autoplay: true,
                path: 'assets/dafoor_logo.json'
            });
        } catch (err) {
            console.error("Lottie player error:", err);
        }

        bindResetEvents();
    }

    function bindResetEvents() {
        const form = document.getElementById('reset-form');
        const submitBtn = document.getElementById('reset-submit-btn');
        const backLink = document.getElementById('back-to-login');

        backLink.addEventListener('click', (e) => {
            e.preventDefault();
            showResetForm = false;
            window.location.hash = '';
            draw();
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const newPassword = document.getElementById('new-password').value;
            const confirmPassword = document.getElementById('confirm-password').value;

            if (newPassword !== confirmPassword) {
                app.showToast('Passwords do not match', 'error');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Resetting...';

            try {
                const response = await app.apiFetch('/api/auth/reset-password', {
                    method: 'POST',
                    body: JSON.stringify({ token: resetToken, new_password: newPassword })
                });

                app.showToast(response.message || 'Password reset successfully!', 'success');
                showResetForm = false;
                window.location.hash = '';
                isLoginMode = true;
                draw();
            } catch (err) {
                app.showToast(err.message, 'error');
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa-solid fa-check"></i> Reset Password';
            }
        });
    }

    function bindEvents() {
        const form = document.getElementById('auth-form');
        const toggleLink = document.getElementById('auth-toggle-link');
        const submitBtn = document.getElementById('auth-submit-btn');

        // Toggle login / sign up
        toggleLink.addEventListener('click', (e) => {
            e.preventDefault();
            isLoginMode = !isLoginMode;
            draw();
        });

        // Form submit (login / signup)
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            const emailEl = document.getElementById('email');
            const email = emailEl ? emailEl.value.trim() : undefined;

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Processing...';

            const endpoint = isLoginMode ? '/api/auth/login' : '/api/auth/signup';
            const bodyData = isLoginMode ? { username, password } : { username, password, email: email || null };
            
            try {
                const response = await app.apiFetch(endpoint, {
                    method: 'POST',
                    body: JSON.stringify(bodyData)
                });
                
                app.showToast(
                    isLoginMode ? 'Logged in successfully!' : 'Account registered and logged in!', 
                    'success'
                );
                
                app.setSession(response.token, response.username);
            } catch (err) {
                app.showToast(err.message, 'error');
                submitBtn.disabled = false;
                submitBtn.innerHTML = isLoginMode 
                    ? '<i class="fa-solid fa-right-to-bracket"></i> Login' 
                    : '<i class="fa-solid fa-user-plus"></i> Sign Up';
            }
        });

        // Forgot password link
        const forgotLink = document.getElementById('forgot-password-link');
        if (forgotLink) {
            forgotLink.addEventListener('click', (e) => {
                e.preventDefault();
                showForgotModal = true;
                const overlay = document.getElementById('forgot-modal-overlay');
                overlay.style.display = 'flex';
                requestAnimationFrame(() => overlay.classList.add('visible'));
            });
        }

        // Close forgot password modal
        const closeBtn = document.getElementById('close-forgot-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                closeForgotModal();
            });
        }

        // Close modal on overlay click
        const overlay = document.getElementById('forgot-modal-overlay');
        if (overlay) {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) closeForgotModal();
            });
        }

        // Forgot password form submit
        const forgotForm = document.getElementById('forgot-form');
        if (forgotForm) {
            forgotForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const email = document.getElementById('forgot-email').value.trim();
                const forgotBtn = document.getElementById('forgot-submit-btn');

                forgotBtn.disabled = true;
                forgotBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Sending...';

                try {
                    const response = await app.apiFetch('/api/auth/forgot-password', {
                        method: 'POST',
                        body: JSON.stringify({ email })
                    });

                    app.showToast(response.message || 'Check your email for the reset link!', 'success');
                    closeForgotModal();
                } catch (err) {
                    app.showToast(err.message, 'error');
                    forgotBtn.disabled = false;
                    forgotBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send Reset Link';
                }
            });
        }

        // Google Sign-In button
        const googleBtn = document.getElementById('google-signin-btn');
        if (googleBtn) {
            googleBtn.addEventListener('click', () => {
                handleGoogleSignIn();
            });
        }
    }

    function closeForgotModal() {
        const overlay = document.getElementById('forgot-modal-overlay');
        if (overlay) {
            overlay.classList.remove('visible');
            setTimeout(() => {
                overlay.style.display = 'none';
                showForgotModal = false;
            }, 300);
        }
    }

    async function handleGoogleSignIn() {
        const googleBtn = document.getElementById('google-signin-btn');

        // Check if Google Identity Services is loaded
        if (!window.google || !window.google.accounts) {
            app.showToast('Google Sign-In is not available. Please check your internet connection.', 'error');
            return;
        }

        googleBtn.disabled = true;
        googleBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Connecting...';

        try {
            // Use Google Identity Services One Tap / popup
            const client = window.google.accounts.oauth2.initTokenClient({
                client_id: window.__GOOGLE_CLIENT_ID || '',
                scope: 'openid email profile',
                callback: async (tokenResponse) => {
                    if (tokenResponse.error) {
                        app.showToast('Google sign-in was cancelled.', 'error');
                        resetGoogleBtn();
                        return;
                    }

                    try {
                        // Get the ID token using the access token
                        const userInfoResp = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                            headers: { 'Authorization': `Bearer ${tokenResponse.access_token}` }
                        });
                        
                        if (!userInfoResp.ok) {
                            throw new Error('Failed to get user info from Google');
                        }

                        // Use the access token flow — send to our backend  
                        // For the id_token approach, we need to use the credential from One Tap
                        // Instead, let's use Google One Tap for the ID token
                        await handleGoogleOneTap();
                    } catch (err) {
                        app.showToast(err.message, 'error');
                        resetGoogleBtn();
                    }
                }
            });

            // Use Google One Tap instead for ID token
            await handleGoogleOneTap();

        } catch (err) {
            app.showToast('Google Sign-In failed. Please try again.', 'error');
            resetGoogleBtn();
        }
    }

    async function handleGoogleOneTap() {
        const googleBtn = document.getElementById('google-signin-btn');

        return new Promise((resolve) => {
            window.google.accounts.id.initialize({
                client_id: window.__GOOGLE_CLIENT_ID || '',
                callback: async (response) => {
                    // response.credential contains the ID token (JWT)
                    try {
                        const result = await app.apiFetch('/api/auth/google', {
                            method: 'POST',
                            body: JSON.stringify({ id_token: response.credential })
                        });

                        const msg = result.is_new_user 
                            ? 'Account created with Google!' 
                            : 'Signed in with Google!';
                        app.showToast(msg, 'success');
                        app.setSession(result.token, result.username);
                    } catch (err) {
                        app.showToast(err.message, 'error');
                        resetGoogleBtn();
                    }
                    resolve();
                },
                auto_select: false,
            });

            // Trigger the One Tap prompt
            window.google.accounts.id.prompt((notification) => {
                if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
                    // If One Tap not available, fall back to the sign-in button render
                    const gBtnContainer = document.createElement('div');
                    gBtnContainer.id = 'g_id_onload_fallback';
                    gBtnContainer.style.display = 'none';
                    document.body.appendChild(gBtnContainer);

                    window.google.accounts.id.renderButton(gBtnContainer, {
                        type: 'standard',
                        size: 'large',
                    });

                    // Click the rendered button programmatically
                    const innerBtn = gBtnContainer.querySelector('[role="button"]') || gBtnContainer.querySelector('div[tabindex]');
                    if (innerBtn) {
                        innerBtn.click();
                    }
                    
                    // Cleanup
                    setTimeout(() => gBtnContainer.remove(), 100);
                    resolve();
                }
            });
        });
    }

    function resetGoogleBtn() {
        const googleBtn = document.getElementById('google-signin-btn');
        if (googleBtn) {
            googleBtn.disabled = false;
            googleBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 48 48">
                    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                </svg>
                <span>${isLoginMode ? 'Sign in with Google' : 'Sign up with Google'}</span>
            `;
        }
    }

    draw();
}
