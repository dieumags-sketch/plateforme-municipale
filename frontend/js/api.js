// frontend/js/api.js

// Configuration de l'API
const API_CONFIG = {
    baseURL: 'http://localhost:8000/api',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
};

// Gestionnaire d'API
class APIClient {
    constructor() {
        this.baseURL = API_CONFIG.baseURL;
    }
    
    getToken() {
        return localStorage.getItem('access_token');
    }
    
    getHeaders() {
        const headers = { ...API_CONFIG.headers };
        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: this.getHeaders()
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || `Erreur ${response.status}`);
            }
            
            return { success: true, data };
        } catch (error) {
            console.error('API Error:', error);
            return { success: false, error: error.message };
        }
    }
    
    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }
    
    post(endpoint, body) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    }
    
    put(endpoint, body) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(body)
        });
    }
    
    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
    
    // ============================================
    // AUTHENTIFICATION
    // ============================================
    
    async login(username, password) {
        const result = await this.post('/accounts/login/', { username, password });
        if (result.success && result.data.token) {
            localStorage.setItem('access_token', result.data.token);
            localStorage.setItem('refresh_token', result.data.refresh_token || result.data.token);
            localStorage.setItem('user', JSON.stringify(result.data.user));
        }
        return result;
    }
    
    async logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/index.html';
    }
    
    getCurrentUser() {
        const user = localStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    }
    
    isAuthenticated() {
        return !!this.getToken();
    }
    
    // ============================================
    // ARCHIVES MODULE
    // ============================================
    
    async getArchives(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const endpoint = `/archives/archives/${queryString ? `?${queryString}` : ''}`;
        return this.get(endpoint);
    }
    
    async getArchiveDetail(archiveId) {
        return this.get(`/archives/archives/${archiveId}/`);
    }
    
    async getCategories() {
        return this.get('/archives/categories/');
    }
    
    async demanderAccesArchive(archiveId, demande) {
        return this.post(`/archives/archives/${archiveId}/demander_acces/`, demande);
    }
    
    async getMesDemandes() {
        return this.get('/archives/demandes/');
    }
    
    async annulerDemande(demandeId) {
        return this.post(`/archives/demandes/${demandeId}/annuler/`, {});
    }
    
    async payerDemande(demandeId) {
        return this.post(`/archives/demandes/${demandeId}/effectuer_paiement/`, {});
    }
    
    async telechargerDocument(demandeId) {
        const token = this.getToken();
        const url = `${this.baseURL}/archives/demandes/${demandeId}/telecharger/`;
        const headers = this.getHeaders();
        
        try {
            const response = await fetch(url, { method: 'GET', headers });
            if (!response.ok) throw new Error('Erreur téléchargement');
            const blob = await response.blob();
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `archive_${demandeId}.pdf`;
            link.click();
            URL.revokeObjectURL(link.href);
            return { success: true };
        } catch (error) {
            console.error('Erreur téléchargement:', error);
            return { success: false, error: error.message };
        }
    }
    
    async incrementerVuesArchive(archiveId) {
        return this.post(`/archives/archives/${archiveId}/incrementer_vues/`, {});
    }
    
    async telechargerParToken(token) {
        const url = `${this.baseURL}/archives/acces/acces/${token}/`;
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Lien invalide ou expiré');
            const blob = await response.blob();
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `document_${token}.pdf`;
            link.click();
            URL.revokeObjectURL(link.href);
            return { success: true };
        } catch (error) {
            console.error('Erreur téléchargement:', error);
            return { success: false, error: error.message };
        }
    }
}

// Instance globale
const api = new APIClient();

// Vérification d'authentification pour pages protégées
document.addEventListener('DOMContentLoaded', () => {
    const protectedPages = ['dashboard.html', 'archives.html', 'etat_civil.html', 
                            'actualites.html', 'annuaires.html', 'activites.html',
                            'signature.html', 'paiements.html', 'dechets.html'];
    
    const currentPage = window.location.pathname.split('/').pop();
    
    if (protectedPages.includes(currentPage) && !api.isAuthenticated()) {
        window.location.href = 'login.html';
    }
    
    // Afficher le nom de l'utilisateur si présent
    const user = api.getCurrentUser();
    const userNameSpan = document.getElementById('userName');
    if (user && userNameSpan) {
        userNameSpan.textContent = `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username;
    }
});

// Déconnexion
document.getElementById('logoutBtn')?.addEventListener('click', (e) => {
    e.preventDefault();
    api.logout();
});