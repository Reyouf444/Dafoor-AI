/* ==========================================================================
   Dafoor AI - Auth Page Component (Vanilla JS)
   ========================================================================== */

export function renderAuth(container, app) {
    let isLoginMode = true;

    function draw() {
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
                        <div class="form-group">
                            <label class="form-label" for="password">Password</label>
                            <input 
                                type="password" 
                                id="password" 
                                class="form-input" 
                                placeholder="••••••••" 
                                required 
                                minlength="6"
                                autocomplete="current-password"
                            />
                        </div>
                        
                        <button type="submit" id="auth-submit-btn" class="btn btn-primary" style="width: 100%; margin-top: 10px;">
                            ${isLoginMode ? '<i class="fa-solid fa-right-to-bracket"></i> Login' : '<i class="fa-solid fa-user-plus"></i> Sign Up'}
                        </button>
                    </form>
                    
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

    function bindEvents() {
        const form = document.getElementById('auth-form');
        const toggleLink = document.getElementById('auth-toggle-link');
        const submitBtn = document.getElementById('auth-submit-btn');

        toggleLink.addEventListener('click', (e) => {
            e.preventDefault();
            isLoginMode = !isLoginMode;
            draw();
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Processing...';

            const endpoint = isLoginMode ? '/api/auth/login' : '/api/auth/signup';
            
            try {
                const response = await app.apiFetch(endpoint, {
                    method: 'POST',
                    body: JSON.stringify({ username, password })
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
    }

    draw();
}
