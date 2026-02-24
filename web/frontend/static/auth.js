/**
 * Authentication Page JavaScript
 * Handles login, registration, and session management
 */

class AuthManager {
    constructor() {
        this.apiBase = '/api';
        this.currentUser = null;
        this.init();
    }

    init() {
        this.setupTabSwitching();
        this.setupFormHandlers();
        this.checkExistingSession();
    }

    setupTabSwitching() {
        const loginTab = document.getElementById('loginTab');
        const registerTab = document.getElementById('registerTab');
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');

        loginTab.addEventListener('click', () => {
            loginTab.classList.add('active');
            registerTab.classList.remove('active');
            loginForm.classList.add('active');
            registerForm.classList.remove('active');
            this.clearMessages();
        });

        registerTab.addEventListener('click', () => {
            registerTab.classList.add('active');
            loginTab.classList.remove('active');
            registerForm.classList.add('active');
            loginForm.classList.remove('active');
            this.clearMessages();
        });
    }

    setupFormHandlers() {
        // Login form
        const loginForm = document.getElementById('loginFormElement');
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        // Register form
        const registerForm = document.getElementById('registerFormElement');
        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegister();
        });

        // Password confirmation validation
        const password = document.getElementById('registerPassword');
        const confirmPassword = document.getElementById('registerConfirmPassword');

        confirmPassword.addEventListener('input', () => {
            if (password.value !== confirmPassword.value) {
                confirmPassword.setCustomValidity('Passwords do not match');
            } else {
                confirmPassword.setCustomValidity('');
            }
        });
    }

    async checkExistingSession() {
        const token = localStorage.getItem('authToken');
        if (token) {
            try {
                const response = await this.apiRequest('/auth/me', {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (response.user) {
                    this.currentUser = response.user;
                    this.onLoginSuccess(response);
                    return;
                }
            } catch (error) {
                // Token invalid, clear it
                localStorage.removeItem('authToken');
            }
        }
    }

    async handleLogin() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;

        if (!username || !password) {
            this.showMessage('loginMessage', 'Please fill in all fields', 'error');
            return;
        }

        this.showLoading(true);

        try {
            const response = await this.apiRequest('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            this.onLoginSuccess(response);
        } catch (error) {
            this.showMessage('loginMessage', error.message || 'Login failed', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async handleRegister() {
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const fullName = document.getElementById('registerFullName').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('registerConfirmPassword').value;

        if (!username || !email || !password || !confirmPassword) {
            this.showMessage('registerMessage', 'Please fill in all required fields', 'error');
            return;
        }

        if (password !== confirmPassword) {
            this.showMessage('registerMessage', 'Passwords do not match', 'error');
            return;
        }

        if (password.length < 6) {
            this.showMessage('registerMessage', 'Password must be at least 6 characters', 'error');
            return;
        }

        this.showLoading(true);

        try {
            const response = await this.apiRequest('/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username,
                    email,
                    password,
                    full_name: fullName || null
                })
            });

            this.onLoginSuccess(response);
        } catch (error) {
            this.showMessage('registerMessage', error.message || 'Registration failed', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    onLoginSuccess(response) {
        // Store auth token
        localStorage.setItem('authToken', response.access_token);
        this.currentUser = response.user;

        // Show success message
        this.showMessage('loginMessage', 'Login successful! Redirecting...', 'success');

        // Redirect to main app after short delay
        setTimeout(() => {
            window.location.href = '/';
        }, 1000);
    }

    async apiRequest(endpoint, options = {}) {
        const url = `${this.apiBase}${endpoint}`;

        const response = await fetch(url, options);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    }

    showMessage(elementId, message, type = 'info') {
        const element = document.getElementById(elementId);
        element.textContent = message;
        element.className = `message ${type}`;
        element.style.display = 'block';
    }

    clearMessages() {
        const messages = document.querySelectorAll('.message');
        messages.forEach(msg => {
            msg.style.display = 'none';
            msg.className = 'message';
        });
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        const buttons = document.querySelectorAll('.auth-button');

        if (show) {
            overlay.style.display = 'flex';
            buttons.forEach(btn => btn.disabled = true);
        } else {
            overlay.style.display = 'none';
            buttons.forEach(btn => btn.disabled = false);
        }
    }

    // Static method to get current user from other pages
    static getCurrentUser() {
        const token = localStorage.getItem('authToken');
        if (!token) return null;

        try {
            // Decode token payload (basic check)
            const payload = JSON.parse(atob(token.split('.')[1]));
            return {
                user_id: payload.sub,
                username: payload.username,
                email: payload.email,
                full_name: payload.full_name
            };
        } catch (e) {
            return null;
        }
    }

    // Static method to logout from other pages
    static async logout() {
        const token = localStorage.getItem('authToken');
        if (token) {
            try {
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
            } catch (e) {
                // Ignore logout errors
            }
        }
        localStorage.removeItem('authToken');
        window.location.href = '/auth.html';
    }
}

// Initialize auth manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AuthManager();
});

// Export for use in other scripts
window.AuthManager = AuthManager;