/* ==========================================================================
   Dafoor AI - Core Application Controller & Router (Vanilla JS)
   ========================================================================== */

import { renderAuth } from './components/auth.js';
import { renderDashboard } from './components/dashboard.js';
import { renderQuizSetup } from './components/quizSetup.js';
import { renderQuizActive } from './components/quizActive.js';
import { renderAnalytics } from './components/analytics.js';
import { renderSettings } from './components/settings.js';
import { renderFlashcards } from './components/flashcards.js';
import { renderLiveQuiz } from './components/liveQuiz.js';

class App {
    constructor() {
        this.state = {
            token: localStorage.getItem('token') || null,
            username: localStorage.getItem('username') || null,
            currentView: 'auth', // auth, dashboard, quiz-setup, quiz-active, analytics, settings
            pdfs: [],
            activeQuiz: null, // Holds active quiz details
            geminiApiKey: localStorage.getItem('gemini_api_key') || ''
        };
        
        this.container = document.getElementById('app-container');
        this.header = document.getElementById('app-header');
        this.userDisplay = document.getElementById('user-display');
        this.logoutBtn = document.getElementById('logout-btn');
        
        this.initEvents();
    }

    async start() {
        // Initialize the navbar Lottie logo animation
        try {
            lottie.loadAnimation({
                container: document.getElementById('logo-animation-nav'),
                renderer: 'svg',
                loop: true,
                autoplay: true,
                path: 'assets/dafoor_logo.json'
            });
        } catch (err) {
            console.error("Failed to load nav logo Lottie animation:", err);
        }

        // Check token validity on boot
        if (this.state.token) {
            try {
                const user = await this.apiFetch('/api/auth/me');
                this.state.username = user.username;
                localStorage.setItem('username', user.username);
                this.updateHeader();
                
                // Route based on URL hash or default to dashboard
                const hash = window.location.hash.substring(1);
                if (['dashboard', 'quiz-setup', 'flashcards', 'live-quiz', 'analytics', 'settings'].includes(hash)) {
                    this.navigateTo(hash);
                } else {
                    this.navigateTo('dashboard');
                }
            } catch (err) {
                console.error("Token verification failed:", err);
                this.logout();
            }
        } else {
            // Check if we're on a password reset page
            const hash = window.location.hash;
            if (hash.startsWith('#reset-password')) {
                this.navigateTo('auth');
            } else {
                this.navigateTo('auth');
            }
        }
    }

    initEvents() {
        // Listen to navigation link clicks
        document.querySelectorAll('.nav-item').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const view = link.getAttribute('href').substring(1);
                this.navigateTo(view);
            });
        });
        
        // Logout button
        if (this.logoutBtn) {
            this.logoutBtn.addEventListener('click', () => this.logout());
        }

        // Settings button
        const settingsBtn = document.getElementById('settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigateTo('settings');
            });
        }

        // Handle browser forward/back buttons (hash changes)
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash.substring(1);
            if (this.state.token && ['dashboard', 'quiz-setup', 'flashcards', 'live-quiz', 'analytics', 'settings'].includes(hash)) {
                if (this.state.currentView !== hash) {
                    this.navigateTo(hash, null, false); // Don't push state since hash changed
                }
            }
        });
    }

    navigateTo(view, params = null, updateHash = true) {
        // Route protection
        if (!this.state.token && view !== 'auth') {
            view = 'auth';
        } else if (this.state.token && view === 'auth') {
            view = 'dashboard';
        }

        this.state.currentView = view;
        
        if (updateHash) {
            if (view === 'auth') {
                // Preserve reset-password hash if present
                if (!window.location.hash.startsWith('#reset-password')) {
                    window.location.hash = '';
                }
            } else if (view !== 'quiz-active') {
                window.location.hash = view;
            }
        }

        this.updateHeader();
        this.renderView(params);
    }

    updateHeader() {
        if (this.state.token && this.state.currentView !== 'auth') {
            this.header.classList.remove('hidden');
            this.userDisplay.innerHTML = `<i class="fa-regular fa-circle-user"></i> ${this.state.username}`;
            
            // Highlight active navigation tab
            document.querySelectorAll('.nav-item').forEach(link => {
                const targetView = link.getAttribute('href').substring(1);
                if (this.state.currentView === targetView) {
                    link.classList.add('active');
                } else {
                    link.classList.remove('active');
                }
            });

            // Highlight settings button if on settings page
            const settingsBtn = document.getElementById('settings-btn');
            if (settingsBtn) {
                if (this.state.currentView === 'settings') {
                    settingsBtn.classList.add('active');
                } else {
                    settingsBtn.classList.remove('active');
                }
            }
        } else {
            this.header.classList.add('hidden');
        }
    }

    async renderView(params) {
        // Clear container and show slide-in transition
        this.container.innerHTML = '<div class="loader-container"><div class="spinner"></div></div>';
        this.container.className = 'fade-in';
        
        try {
            switch (this.state.currentView) {
                case 'auth':
                    renderAuth(this.container, this);
                    break;
                case 'dashboard':
                    await renderDashboard(this.container, this);
                    break;
                case 'quiz-setup':
                    await renderQuizSetup(this.container, this);
                    break;
                case 'quiz-active':
                    renderQuizActive(this.container, this, params);
                    break;
                case 'analytics':
                    await renderAnalytics(this.container, this);
                    break;
                case 'flashcards':
                    await renderFlashcards(this.container, this);
                    break;
                case 'live-quiz':
                    await renderLiveQuiz(this.container, this, params);
                    break;
                case 'settings':
                    await renderSettings(this.container, this);
                    break;
                default:
                    this.container.innerHTML = '<h2>404 - View Not Found</h2>';
            }
        } catch (err) {
            console.error(`Error rendering view ${this.state.currentView}:`, err);
            this.container.innerHTML = `
                <div class="card" style="text-align: center;">
                    <h2>Rendering Error</h2>
                    <p style="margin: 16px 0;">Something went wrong loading this screen: ${err.message}</p>
                    <button class="btn btn-primary" onclick="window.location.reload()">Reload Application</button>
                </div>
            `;
        }
    }

    // --- API Service Client ---
    async apiFetch(url, options = {}) {
        const headers = { ...options.headers };
        
        // Automatically inject Auth Bearer token if session exists
        if (this.state.token) {
            headers['Authorization'] = `Bearer ${this.state.token}`;
        }
        
        // Default content type to JSON unless uploading a file
        if (!(options.body instanceof FormData) && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }
        
        const fetchOptions = {
            ...options,
            headers
        };
        
        const response = await fetch(url, fetchOptions);
        
        if (response.status === 401 && this.state.currentView !== 'auth') {
            this.logout();
            throw new Error("Session expired. Please log in again.");
        }
        
        // Safely parse JSON — Cloud Run may return HTML error pages (502/503)
        let responseData;
        const contentType = response.headers.get('content-type') || '';
        try {
            if (contentType.includes('application/json')) {
                responseData = await response.json();
            } else {
                const text = await response.text();
                try {
                    responseData = JSON.parse(text);
                } catch {
                    // Non-JSON response (e.g. HTML error page from Cloud Run)
                    throw new Error(
                        response.ok 
                            ? "Unexpected server response format" 
                            : `Server error (${response.status}): ${text.substring(0, 120)}`
                    );
                }
            }
        } catch (parseErr) {
            if (parseErr.message.includes('Server error') || parseErr.message.includes('Unexpected server')) {
                throw parseErr;
            }
            throw new Error(`Server error (${response.status}): Could not parse response`);
        }
        
        if (!response.ok) {
            throw new Error(responseData.detail || `Server error (${response.status})`);
        }
        
        return responseData;
    }

    // --- Global Notifications System ---
    showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = type === 'success' 
            ? '<i class="fa-solid fa-circle-check"></i>' 
            : '<i class="fa-solid fa-triangle-exclamation"></i>';
            
        toast.innerHTML = `${icon} <span>${message}</span>`;
        container.appendChild(toast);
        
        // Remove toast automatically after duration
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(20px)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // --- Global Actions ---
    setSession(token, username) {
        this.state.token = token;
        this.state.username = username;
        localStorage.setItem('token', token);
        localStorage.setItem('username', username);
        this.navigateTo('dashboard');
    }

    async logout() {
        try {
            await this.apiFetch('/api/auth/logout', { method: 'POST' });
        } catch (err) {
            console.warn("Logout request failed:", err);
        }
        
        this.state.token = null;
        this.state.username = null;
        this.state.activeQuiz = null;
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        
        this.navigateTo('auth');
    }
}

// Instantiate and start app on DOM load
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
    window.app = app; // Expose for easy debugging
    app.start();
});
