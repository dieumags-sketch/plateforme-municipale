// frontend/js/modules/auth.js

const API_BASE = 'http://localhost:8000/api/accounts';

// Configuration de l'API avec token
let authToken = localStorage.getItem('auth_token');

function setAuthToken(token) {
    authToken = token;
    if (token) {
        localStorage.setItem('auth_token', token);
    } else {
        localStorage.removeItem('auth_token');
    }
}

function getAuthHeaders() {
    const headers = {
        'Content-Type': 'application/json'
    };
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    return headers;
}

// Vérifier si l'utilisateur est connecté
function isAuthenticated() {
    return !!authToken;
}

// Rediriger si non connecté
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/pages/accounts/login.html';
        return false;
    }
    return true;
}

// Rediriger si connecté
function requireGuest() {
    if (isAuthenticated()) {
        window.location.href = '/dashboard.html';
        return false;
    }
    return true;
}

// Connexion classique
async function login(emailOrUsername, password, totpCode = null) {
    try {
        const response = await fetch(`${API_BASE}/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: emailOrUsername,
                password: password,
                totp_code: totpCode,
                device_name: getDeviceName(),
                device_type: getDeviceType()
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            setAuthToken(data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            localStorage.setItem('session_id', data.session_id);
            showToast('Connexion réussie !', 'success');
            
            // Redirection vers la page précédente ou dashboard
            const redirect = sessionStorage.getItem('redirect_after_login') || '/dashboard.html';
            sessionStorage.removeItem('redirect_after_login');
            window.location.href = redirect;
            return { success: true };
        } else {
            // Vérifier si 2FA est requis
            if (data.requires_2fa) {
                return { success: false, requires_2fa: true };
            }
            showToast(data.error || 'Identifiants invalides', 'error');
            return { success: false };
        }
    } catch (error) {
        console.error('Erreur connexion:', error);
        showToast('Erreur de connexion au serveur', 'error');
        return { success: false };
    }
}

// Inscription
async function register(userData) {
    try {
        const response = await fetch(`${API_BASE}/register/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            setAuthToken(data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            showToast(data.message || 'Inscription réussie !', 'success');
            window.location.href = '/pages/accounts/verify-email-sent.html';
            return { success: true };
        } else {
            const errors = Object.values(data).flat().join(', ');
            showToast(errors || 'Erreur lors de l\'inscription', 'error');
            return { success: false, errors: data };
        }
    } catch (error) {
        console.error('Erreur inscription:', error);
        showToast('Erreur de connexion au serveur', 'error');
        return { success: false };
    }
}

// Déconnexion
async function logout() {
    const sessionId = localStorage.getItem('session_id');
    
    try {
        await fetch(`${API_BASE}/logout/`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ session_id: sessionId })
        });
    } catch (error) {
        console.error('Erreur déconnexion:', error);
    }
    
    // Nettoyer le stockage local
    setAuthToken(null);
    localStorage.removeItem('user');
    localStorage.removeItem('session_id');
    
    window.location.href = '/index.html';
}

// Obtenir l'utilisateur courant
function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

// Mettre à jour le profil
async function updateProfile(profileData) {
    try {
        const response = await fetch(`${API_BASE}/profile/`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(profileData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            localStorage.setItem('user', JSON.stringify(data));
            showToast('Profil mis à jour', 'success');
            return { success: true, user: data };
        } else {
            showToast('Erreur lors de la mise à jour', 'error');
            return { success: false };
        }
    } catch (error) {
        console.error('Erreur mise à jour:', error);
        return { success: false };
    }
}

// Changer mot de passe
async function changePassword(oldPassword, newPassword) {
    try {
        const response = await fetch(`${API_BASE}/change-password/`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                old_password: oldPassword,
                new_password: newPassword,
                confirm_password: newPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Mot de passe modifié', 'success');
            return { success: true };
        } else {
            showToast(data.error || 'Erreur', 'error');
            return { success: false };
        }
    } catch (error) {
        console.error('Erreur:', error);
        return { success: false };
    }
}

// Mot de passe oublié
async function forgotPassword(email) {
    try {
        const response = await fetch(`${API_BASE}/forgot-password/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        showToast(data.message, 'success');
        return { success: true };
    } catch (error) {
        console.error('Erreur:', error);
        return { success: false };
    }
}

// Réinitialiser mot de passe
async function resetPassword(token, newPassword) {
    try {
        const response = await fetch(`${API_BASE}/reset-password/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                token,
                new_password: newPassword,
                confirm_password: newPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Mot de passe réinitialisé', 'success');
            window.location.href = '/pages/accounts/login.html';
            return { success: true };
        } else {
            showToast(data.error || 'Erreur', 'error');
            return { success: false };
        }
    } catch (error) {
        console.error('Erreur:', error);
        return { success: false };
    }
}

// Envoyer code SMS
async function sendPhoneCode(phone) {
    try {
        const response = await fetch(`${API_BASE}/send-phone-code/`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ phone })
        });
        
        const data = await response.json();
        showToast(data.message, 'success');
        return { success: true };
    } catch (error) {
        console.error('Erreur:', error);
        return { success: false };
    }
}

// Vérifier code SMS
async function verifyPhone(code) {
    try {
        const response = await fetch(`${API_BASE}/verify-phone/`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ code })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Téléphone vérifié', 'success');
            return { success: true };
        } else {
            showToast(data.error || 'Code invalide', 'error');
            return { success: false };
        }
    } catch (error) {
        console.error('Erreur:', error);
        return { success: false };
    }
}

// Activer 2FA
async function enable2FA(code) {
    try {
        const response = await fetch(`${API_BASE}/2fa/enable/`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ code })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('2FA activé', 'success');
            return { success: true };
        } else {
            showToast(data.error || 'Code invalide', 'error');
            return { success: false };
        }
    } catch (error) {
        console.error('Erreur:', error);
        return { success: false };
    }
}

// Désactiver 2FA
async function disable2FA() {
    try {
        await fetch(`${API_BASE}/2fa/disable/`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        showToast('2FA désactivé', 'success');
        return { success: true };
    } catch (error) {
        console.error('Erreur:', error);
        return { success: false };
    }
}

// Obtenir les sessions
async function getSessions() {
    try {
        const response = await fetch(`${API_BASE}/sessions/`, {
            headers: getAuthHeaders()
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Erreur:', error);
        return [];
    }
}

// Terminer une session
async function terminateSession(sessionId) {
    try {
        await fetch(`${API_BASE}/sessions/${sessionId}/`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        showToast('Session terminée', 'success');
        return { success: true };
    } catch (error) {
        console.error('Erreur:', error);
        return { success: false };
    }
}

// Utilitaires
function getDeviceName() {
    const userAgent = navigator.userAgent;
    if (/iPhone|iPad|iPod/.test(userAgent)) return 'iOS Device';
    if (/Android/.test(userAgent)) return 'Android Device';
    if (/Windows/.test(userAgent)) return 'Windows PC';
    if (/Mac/.test(userAgent)) return 'Mac';
    return 'Unknown Device';
}

function getDeviceType() {
    const userAgent = navigator.userAgent;
    if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(userAgent)) return 'tablet';
    if (/Mobile|Android|iP(hone|od)|IEMobile|BlackBerry|Kindle|Silk-Accelerated|(hpw|web)OS|Opera M(ob|in)i/.test(userAgent)) return 'mobile';
    return 'desktop';
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i> ${message}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Initialisation des événements sur les pages d'auth
document.addEventListener('DOMContentLoaded', () => {
    // Toggle password visibility
    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = btn.previousElementSibling;
            const type = input.type === 'password' ? 'text' : 'password';
            input.type = type;
            btn.querySelector('i').classList.toggle('fa-eye');
            btn.querySelector('i').classList.toggle('fa-eye-slash');
        });
    });
    
    // Formulaire de connexion classique
    const loginForm = document.getElementById('classic-login');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('login-username').value;
            const password = document.getElementById('login-password').value;
            const totpCode = document.getElementById('totp-code')?.value;
            
            const result = await login(username, password, totpCode);
            
            if (result.requires_2fa) {
                document.getElementById('totp-group').style.display = 'block';
                showToast('Code 2FA requis', 'info');
            }
        });
    }
    
    // Formulaire d'inscription
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const password = document.getElementById('reg-password').value;
            const confirmPassword = document.getElementById('reg-confirm-password').value;
            
            if (password !== confirmPassword) {
                showToast('Les mots de passe ne correspondent pas', 'error');
                return;
            }
            
            const userData = {
                email: document.getElementById('reg-email').value,
                username: document.getElementById('reg-username').value,
                nom: document.getElementById('reg-nom').value,
                prenom: document.getElementById('reg-prenom').value,
                telephone: document.getElementById('reg-phone')?.value || '',
                password: password,
                password2: confirmPassword
            };
            
            await register(userData);
        });
    }
    
    // Formulaire mot de passe oublié
    const forgotForm = document.getElementById('forgot-form');
    if (forgotForm) {
        forgotForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('forgot-email').value;
            await forgotPassword(email);
        });
    }
    
    // Formulaire réinitialisation
    const resetForm = document.getElementById('reset-form');
    if (resetForm) {
        resetForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const urlParams = new URLSearchParams(window.location.search);
            const token = urlParams.get('token');
            
            const newPassword = document.getElementById('reset-password').value;
            const confirmPassword = document.getElementById('reset-confirm-password').value;
            
            if (newPassword !== confirmPassword) {
                showToast('Les mots de passe ne correspondent pas', 'error');
                return;
            }
            
            await resetPassword(token, newPassword);
        });
    }
});

// Exporter les fonctions pour usage global
window.auth = {
    isAuthenticated,
    requireAuth,
    requireGuest,
    login,
    register,
    logout,
    getCurrentUser,
    updateProfile,
    changePassword,
    forgotPassword,
    resetPassword,
    sendPhoneCode,
    verifyPhone,
    enable2FA,
    disable2FA,
    getSessions,
    terminateSession,
    getAuthHeaders
};