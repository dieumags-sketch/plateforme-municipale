// frontend/js/modules/passkey.js

async function registerPasskey() {
    try {
        // Demander la création d'une clé au navigateur
        const publicKeyCredentialCreationOptions = {
            challenge: Uint8Array.from(crypto.getRandomValues(new Uint8Array(32))),
            rp: { name: "Plateforme Municipale", id: window.location.hostname },
            user: {
                id: Uint8Array.from(crypto.getRandomValues(new Uint8Array(16))),
                name: getCurrentUser()?.email,
                displayName: getCurrentUser()?.full_name
            },
            pubKeyCredParams: [
                { type: "public-key", alg: -7 },  // ES256
                { type: "public-key", alg: -257 } // RS256
            ],
            authenticatorSelection: {
                authenticatorAttachment: "platform",
                userVerification: "required",
                residentKey: "required"
            },
            timeout: 60000,
            attestation: "direct"
        };
        
        const credential = await navigator.credentials.create({
            publicKey: publicKeyCredentialCreationOptions
        });
        
        // Envoyer au backend
        const response = await fetch(`${API_BASE}/passkey/register/`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                credential_id: arrayBufferToBase64(credential.rawId),
                public_key: credential.response,
                device_name: getDeviceName()
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Clé de sécurité enregistrée', 'success');
            return true;
        } else {
            showToast(data.error || 'Erreur', 'error');
            return false;
        }
    } catch (error) {
        console.error('Erreur création passkey:', error);
        showToast('Annulé ou erreur', 'error');
        return false;
    }
}

async function loginWithPasskey() {
    try {
        // Demander l'utilisation d'une clé
        const publicKeyCredentialRequestOptions = {
            challenge: Uint8Array.from(crypto.getRandomValues(new Uint8Array(32))),
            rpId: window.location.hostname,
            allowCredentials: [],
            userVerification: "required",
            timeout: 60000
        };
        
        const assertion = await navigator.credentials.get({
            publicKey: publicKeyCredentialRequestOptions
        });
        
        // Envoyer au backend pour authentification
        const response = await fetch(`${API_BASE}/passkey/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                credential_id: arrayBufferToBase64(assertion.rawId),
                authenticator_data: arrayBufferToBase64(assertion.response.authenticatorData),
                client_data_json: arrayBufferToBase64(assertion.response.clientDataJSON),
                signature: arrayBufferToBase64(assertion.response.signature)
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            setAuthToken(data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            showToast('Connexion avec clé réussie', 'success');
            window.location.href = '/dashboard.html';
            return true;
        } else {
            showToast(data.error || 'Clé invalide', 'error');
            return false;
        }
    } catch (error) {
        console.error('Erreur connexion passkey:', error);
        showToast('Annulé ou erreur', 'error');
        return false;
    }
}

function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    const passkeyLoginBtn = document.getElementById('passkey-login-btn');
    if (passkeyLoginBtn) {
        passkeyLoginBtn.addEventListener('click', loginWithPasskey);
    }
    
    const registerPasskeyBtn = document.getElementById('register-passkey');
    if (registerPasskeyBtn) {
        registerPasskeyBtn.addEventListener('click', registerPasskey);
    }
});