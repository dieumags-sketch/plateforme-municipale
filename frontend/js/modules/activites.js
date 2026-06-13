// frontend/js/modules/activites.js

const API_BASE = 'http://localhost:8000/api/activites';

// Configuration
let currentPage = 1;
let currentFilters = {
    type_activite: '',
    ville: '',
    est_gratuit: null,
    search: ''
};

// Chargement des activités
async function loadActivites() {
    const grid = document.getElementById('activites-grid');
    if (!grid) return;
    
    grid.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        let url = `${API_BASE}/activites/?page=${currentPage}`;
        if (currentFilters.type_activite) url += `&type_activite=${currentFilters.type_activite}`;
        if (currentFilters.ville) url += `&ville=${currentFilters.ville}`;
        if (currentFilters.est_gratuit !== null) url += `&est_gratuit=${currentFilters.est_gratuit}`;
        if (currentFilters.search) url += `&search=${encodeURIComponent(currentFilters.search)}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            renderActivites(data.results);
            renderPagination(data);
        } else {
            grid.innerHTML = '<div class="no-results">Aucune activité trouvée</div>';
        }
    } catch (error) {
        console.error('Erreur:', error);
        grid.innerHTML = '<div class="error">Erreur de chargement</div>';
    }
}

function renderActivites(activites) {
    const grid = document.getElementById('activites-grid');
    grid.innerHTML = activites.map(act => `
        <div class="activity-card">
            <div class="activity-image">
                <img src="${act.image_principale || 'https://via.placeholder.com/400x200'}" alt="${act.titre}">
                ${act.est_gratuit ? '<span class="activity-badge gratuit">GRATUIT</span>' : ''}
                ${act.places_restantes === 0 ? '<span class="activity-badge complet">COMPLET</span>' : ''}
            </div>
            <div class="activity-content">
                <div class="activity-type">${getTypeIcon(act.type_activite)} ${getTypeLabel(act.type_activite)}</div>
                <h3 class="activity-title"><a href="detail.html?id=${act.id}">${escapeHtml(act.titre)}</a></h3>
                <div class="activity-info">
                    <span><i class="fas fa-calendar"></i> ${formatDate(act.date_debut)}</span>
                    <span><i class="fas fa-map-marker-alt"></i> ${act.lieu}, ${act.ville}</span>
                </div>
                <div class="activity-price">
                    ${act.est_gratuit ? 'GRATUIT' : `${act.prix.toLocaleString()} FCFA`}
                </div>
                <div class="activity-footer">
                    <span><i class="fas fa-users"></i> ${act.nb_inscrits || 0} inscrits</span>
                    <a href="detail.html?id=${act.id}" class="btn-sm">Voir détails</a>
                </div>
            </div>
        </div>
    `).join('');
}

// Page détail
async function loadActiviteDetail() {
    const urlParams = new URLSearchParams(window.location.search);
    const activiteId = urlParams.get('id');
    
    if (!activiteId) return;
    
    const container = document.getElementById('detail-container');
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        // Incrémenter la vue
        await fetch(`${API_BASE}/activites/${activiteId}/increment_vue/`, { method: 'POST' });
        
        // Charger détails
        const response = await fetch(`${API_BASE}/activites/${activiteId}/`);
        const act = await response.json();
        
        renderDetail(act);
        
        // Vérifier si déjà inscrit
        const inscritResponse = await fetch(`${API_BASE}/activites/${activiteId}/est_inscrit/`);
        const inscritData = await inscritResponse.json();
        
        if (inscritData.inscrit) {
            document.getElementById('inscription-btn').style.display = 'none';
            document.getElementById('deja-inscrit').style.display = 'block';
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        container.innerHTML = '<div class="error">Impossible de charger l\'activité</div>';
    }
}

function renderDetail(act) {
    const container = document.getElementById('detail-container');
    container.innerHTML = `
        <div class="detail-container">
            <div class="detail-header">
                <div class="detail-type">${getTypeIcon(act.type_activite)} ${getTypeLabel(act.type_activite)}</div>
                <h1 class="detail-title">${escapeHtml(act.titre)}</h1>
                <div class="detail-meta">
                    <div class="detail-meta-item"><i class="fas fa-calendar"></i> ${formatDateTime(act.date_debut)}</div>
                    <div class="detail-meta-item"><i class="fas fa-map-marker-alt"></i> ${act.lieu}, ${act.ville}</div>
                    <div class="detail-meta-item"><i class="fas fa-users"></i> ${act.nb_inscrits || 0} participants</div>
                    <div class="detail-meta-item"><i class="fas fa-eye"></i> ${act.vue_count} vues</div>
                </div>
            </div>
            
            <div class="detail-image">
                <img src="${act.image_principale || 'https://via.placeholder.com/800x400'}" alt="${act.titre}">
            </div>
            
            <div class="detail-description">
                <h3>Description</h3>
                <p>${act.description_longue || act.description_courte}</p>
            </div>
            
            <div class="inscription-panel">
                <h3>Inscription</h3>
                <p><strong>💰 Prix :</strong> ${act.est_gratuit ? 'GRATUIT' : `${act.prix.toLocaleString()} FCFA`}</p>
                <p><strong>📅 Date limite :</strong> ${formatDateTime(act.date_limite_inscription)}</p>
                <p><strong>🎟️ Places restantes :</strong> ${act.places_restantes === -1 ? 'Illimité' : act.places_restantes}</p>
                
                <button id="inscription-btn" class="btn-primary" ${act.places_restantes === 0 ? 'disabled' : ''}>
                    ${act.places_restantes === 0 ? 'Complet' : (act.est_gratuit ? 'S\'inscrire gratuitement' : 'S\'inscrire et payer')}
                </button>
                <div id="deja-inscrit" style="display:none; background:#d1fae5; padding:1rem; border-radius:12px;">
                    ✅ Vous êtes déjà inscrit à cette activité
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('inscription-btn')?.addEventListener('click', () => {
        window.location.href = `inscription.html?id=${act.id}`;
    });
}

// Formulaire d'inscription
async function submitInscription(event) {
    event.preventDefault();
    
    const activiteId = document.getElementById('activite_id').value;
    const nombrePlaces = parseInt(document.getElementById('nombre_places').value);
    
    const formData = {
        activite: activiteId,
        nom_complet: document.getElementById('nom_complet').value,
        email: document.getElementById('email').value,
        telephone: document.getElementById('telephone').value,
        date_naissance: document.getElementById('date_naissance').value,
        adresse: document.getElementById('adresse').value,
        commentaire: document.getElementById('commentaire').value,
        nombre_places: nombrePlaces,
        noms_accompagnants: document.getElementById('noms_accompagnants').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/inscriptions/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (data.montant_total > 0) {
                // Rediriger vers paiement
                window.location.href = `paiement.html?id=${data.id}&montant=${data.montant_total}`;
            } else {
                showToast('Inscription confirmée !', 'success');
                window.location.href = 'mes-inscriptions.html';
            }
        } else {
            showToast(data.error || 'Erreur lors de l\'inscription', 'error');
        }
    } catch (error) {
        showToast('Erreur de connexion', 'error');
    }
}

// Paiement
async function initierPaiement() {
    const inscriptionId = document.getElementById('inscription_id').value;
    const moyenPaiement = document.querySelector('input[name="moyen_paiement"]:checked').value;
    const telephone = document.getElementById('telephone_paiement').value;
    
    try {
        const response = await fetch(`${API_BASE}/paiements/initier/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
            },
            body: JSON.stringify({
                inscription_id: inscriptionId,
                moyen_paiement: moyenPaiement,
                numero_telephone: telephone
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Paiement initié. Confirmez sur votre téléphone.', 'success');
            // Simuler confirmation après 5 secondes
            setTimeout(() => confirmerPaiement(data.paiement_id), 5000);
        } else {
            showToast(data.error || 'Erreur de paiement', 'error');
        }
    } catch (error) {
        showToast('Erreur de connexion', 'error');
    }
}

async function confirmerPaiement(paiementId) {
    try {
        const response = await fetch(`${API_BASE}/paiements/confirmer/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
            },
            body: JSON.stringify({ paiement_id: paiementId })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Paiement confirmé ! Inscription validée.', 'success');
            window.location.href = 'mes-inscriptions.html';
        }
    } catch (error) {
        console.error('Erreur:', error);
    }
}

// Utilitaires
function getTypeIcon(type) {
    const icons = {
        sante: '🏥', formation: '📚', culturel: '🎭',
        sportif: '⚽', social: '🤝', environnement: '🌱',
        citoyen: '🗳️', autre: '📌'
    };
    return icons[type] || '📌';
}

function getTypeLabel(type) {
    const labels = {
        sante: 'Santé', formation: 'Formation', culturel: 'Culturel',
        sportif: 'Sportif', social: 'Social', environnement: 'Environnement',
        citoyen: 'Citoyen', autre: 'Autre'
    };
    return labels[type] || type;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i> ${message}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('activites-grid')) loadActivites();
    if (document.getElementById('detail-container')) loadActiviteDetail();
    if (document.getElementById('inscription-form')) {
        document.getElementById('inscription-form').addEventListener('submit', submitInscription);
    }
    if (document.getElementById('paiement-form')) {
        document.getElementById('paiement-form').addEventListener('submit', (e) => {
            e.preventDefault();
            initierPaiement();
        });
    }
});