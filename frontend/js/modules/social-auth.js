// frontend/js/modules/social-auth.js

// Configuration OAuth
const SOCIAL_CONFIG = {
    google: {
        clientId: 'VOTRE_GOOGLE_CLIENT_ID',
        scope: 'email profile',
        authUrl: 'https://accounts.google.com/o/oauth2/v2/auth'
    },
    facebook: {
        clientId: 'VOTRE_FACEBOOK_APP_ID',
        scope: 'email public_profile',
        authUrl: 'https://www.facebook.com/v18.0/dialog/oauth'
    }
};

async function loginWithGoogle() {
    // Utiliser l'API Google Identity Services
    if (window.google) {
        const client = google.accounts.oauth2.initTokenClient({
            client_id: SOCIAL_CONFIG.google.clientId,
            scope: SOCIAL_CONFIG.google.scope,
            callback: async (tokenResponse) => {
                await socialLogin('google', tokenResponse.access_token);
            }
        });
        client.requestAccessToken();
    } else {
        // Fallback: redirection OAuth
        const redirectUri = `${window.location.origin}/pages/accounts/social-callback.html`;
        const url = `${SOCIAL_CONFIG.google.authUrl}?client_id=${SOCIAL_CONFIG.google.clientId}&redirect_uri=${redirectUri}&response_type=token&scope=${SOCIAL_CONFIG.google.scope}`;
        window.location.href = url;
    }
}

async function loginWithFacebook() {
    // Initialiser Facebook SDK
    FB.login(async (response) => {
        if (response.authResponse) {
            await socialLogin('facebook', response.authResponse.accessToken);
        }
    }, { scope: SOCIAL_CONFIG.facebook.scope });
}

async function loginWithApple() {
    // Apple Sign-In
    const config = {
        clientId: 'VOTRE_APPLE_CLIENT_ID',
        redirectURI: `${window.location.origin}/pages/accounts/social-callback.html`,
        scope: 'name email',
        responseType: 'code id_token',
        responseMode: 'form_post'
    };
    
    const url = `https://appleid.apple.com/auth/authorize?client_id=${config.clientId}&redirect_uri=${config.redirectURI}&response_type=${config.responseType}&scope=${config.scope}&response_mode=${config.responseMode}`;
    window.location.href = url;
}

async function socialLogin(provider, token) {
    try {
        const response = await fetch(`${API_BASE}/social/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider, token })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            setAuthToken(data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            showToast(`Connexion avec ${provider} réussie`, 'success');
            window.location.href = '/dashboard.html';
        } else {
            showToast(data.error || 'Erreur de connexion sociale', 'error');
        }
    } catch (error) {
        console.error('Erreur social login:', error);
        showToast('Erreur de connexion', 'error');
    }
}

// Charger les SDK
function loadGoogleSDK() {
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
}

function loadFacebookSDK() {
    window.fbAsyncInit = function() {
        FB.init({
            appId: SOCIAL_CONFIG.facebook.clientId,
            cookie: true,
            xfbml: true,
            version: 'v18.0'
        });
    };
    
    const script = document.createElement('script');
    script.src = 'https://connect.facebook.net/fr_FR/sdk.js';
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    loadGoogleSDK();
    loadFacebookSDK();
    
    const googleBtn =ls document.getElementById('google-login');
    if (googleBtn) googleBtn.addEventListener('click', loginWithGoogle);
    
    const facebookBtn = document.getElementById('facebook-login');
    if (facebookBtn) facebookBtn.addEventListener('click', loginWithFacebook);
    
    const appleBtn = document.getElementById('apple-login');
    if (appleBtn) appleBtn.addEventListener('click', loginWithApple);
});