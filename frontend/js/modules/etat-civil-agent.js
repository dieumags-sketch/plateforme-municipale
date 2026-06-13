/**
 * AGENT ÉTAT CIVIL - Traitement des demandes citoyennes
 */

let currentPage = 1;
let currentDemande = null;

document.addEventListener('DOMContentLoaded', () => {
    loadDemandes();
    initEventListeners();
});

function initEventListeners() {
    document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') loadDemandes(e.target.value);
    });
}

async function loadDemandes(search = '') {
    const token = localStorage.getItem('access_token');
    const container = document.getElementById('demandesList');
    if (!container) return;
    
    container.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement...</p></div>';
    
    try {
        let url = `http://localhost:8000/api/etat-civil/demandes/?page=${currentPage}&statut=en_attente`;
        if (search) url += `&search=${search}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            displayDemandes(data.results);
            displayPagination(data.count);
        } else {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-check-circle"></i><p>Aucune demande en attente</p></div>';
        }
    } catch (error) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Erreur de chargement</p></div>';
    }
}

function displayDemandes(demandes) {
    const container = document.getElementById('demandesList');
    container.innerHTML = '';
    
    demandes.forEach(demande => {
        const item = document.createElement('div');
        item.className = 'demande-item';
        item.style.borderLeftColor = '#f59e0b';
        
        const typeLabel = {
            'naissance': 'Acte de naissance', 'mariage': 'Acte de mariage',
            'deces': 'Acte de décès', 'reconnaissance': 'Reconnaissance',
            'adoption': 'Adoption'
        }[demande.type_acte] || demande.type_acte;
        
        item.innerHTML = `
            <div class="demande-header">
                <div class="demande-statut statut-en_attente">
                    <i class="fas fa-clock"></i> En attente
                </div>
                <div class="demande-date">${new Date(demande.date_creation).toLocaleDateString('fr-FR')}</div>
            </div>
            <div class="archive-reference">${demande.reference}</div>
            <div class="archive-titre">${typeLabel}</div>
            <div class="demande-details">
                <span><i class="fas fa-user"></i> ${demande.demandeur_nom || 'Citoyen'}</span>
                <span><i class="fas fa-money-bill-wave"></i> ${demande.tarif_calcule || 0} FCFA</span>
            </div>
            <div class="demande-actions">
                <button class="btn-download" onclick="traiterDemande('${demande.id}')">
                    <i class="fas fa-check-circle"></i> Vérifier et valider
                </button>
            </div>
        `;
        container.appendChild(item);
    });
}

function displayPagination(total) {
    const pagination = document.getElementById('pagination');
    if (!pagination) return;
    
    const totalPages = Math.ceil(total / 10);
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = '';
    html += `<button ${currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${currentPage - 1})">&laquo;</button>`;
    for (let i = 1; i <= Math.min(totalPages, 5); i++) {
        html += `<button class="${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }
    html += `<button ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">&raquo;</button>`;
    pagination.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    loadDemandes();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function traiterDemande(demandeId) {
    const token = localStorage.getItem('access_token');
    const modal = document.getElementById('traitementModal');
    const modalBody = document.getElementById('modalBody');
    
    modalBody.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement...</p></div>';
    modal.classList.add('active');
    
    try {
        const response = await fetch(`http://localhost:8000/api/etat-civil/demandes/${demandeId}/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const demande = await response.json();
        currentDemande = demande;
        
        const data = demande.data;
        let detailsHtml = '<div class="detail-section"><h4>Informations</h4>';
        
        if (demande.type_acte === 'naissance') {
            detailsHtml += `
                <p><strong>Enfant:</strong> ${data.enfant_nom || ''} ${data.enfant_prenom || ''}</p>
                <p><strong>Date naissance:</strong> ${data.enfant_date_naissance || ''}</p>
                <p><strong>Mère:</strong> ${data.mere_nom || ''} ${data.mere_prenom || ''}</p>
                <p><strong>Père:</strong> ${data.pere_nom || ''} ${data.pere_prenom || ''}</p>
            `;
        } else if (demande.type_acte === 'mariage') {
            detailsHtml += `
                <p><strong>Époux:</strong> ${data.epoux_nom || ''} ${data.epoux_prenom || ''}</p>
                <p><strong>Épouse:</strong> ${data.epouse_nom || ''} ${data.epouse_prenom || ''}</p>
                <p><strong>Date mariage:</strong> ${data.date_mariage || ''}</p>
            `;
        } else if (demande.type_acte === 'deces') {
            detailsHtml += `
                <p><strong>Défunt:</strong> ${data.defunt_nom || ''} ${data.defunt_prenom || ''}</p>
                <p><strong>Date décès:</strong> ${data.date_deces || ''}</p>
                <p><strong>Lieu:</strong> ${data.lieu_deces || ''}</p>
            `;
        }
        detailsHtml += '</div>';
        
        modalBody.innerHTML = `
            ${detailsHtml}
            <div class="form-group">
                <label>Décision</label>
                <select id="actionSelect" class="filter-select">
                    <option value="valider">✅ Valider la demande (conforme)</option>
                    <option value="rejeter">❌ Rejeter la demande (non conforme)</option>
                </select>
            </div>
            <div class="form-group">
                <label>Commentaire (pour rejet)</label>
                <textarea id="commentaire" class="demande-textarea" rows="3" placeholder="Motif du rejet..."></textarea>
            </div>
            <div class="demande-actions" style="margin-top: 20px;">
                <button class="btn-primary" onclick="soumettreTraitement()">Confirmer</button>
                <button class="btn-cancel" onclick="closeModal()">Annuler</button>
            </div>
        `;
    } catch (error) {
        modalBody.innerHTML = '<div class="empty-state"><p>Erreur de chargement</p></div>';
    }
}

async function soumettreTraitement() {
    if (!currentDemande) return;
    
    const action = document.getElementById('actionSelect').value;
    const commentaire = document.getElementById('commentaire').value;
    
    if (action === 'rejeter' && !commentaire) {
        showNotification('Veuillez indiquer un motif de rejet', 'error');
        return;
    }
    
    const token = localStorage.getItem('access_token');
    showNotification('Traitement en cours...', 'info');
    
    try {
        const response = await fetch(`http://localhost:8000/api/etat-civil/demandes/${currentDemande.id}/traiter_agent/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ action, commentaire })
        });
        
        if (response.ok) {
            showNotification('Demande traitée avec succès', 'success');
            closeModal();
            loadDemandes();
        } else {
            showNotification('Erreur lors du traitement', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

function closeModal() {
    document.getElementById('traitementModal').classList.remove('active');
    currentDemande = null;
}

function showNotification(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i> ${message}`;
    toast.style.cssText = `position:fixed; bottom:20px; right:20px; padding:12px 20px; background:${type === 'success' ? '#10b981' : '#ef4444'}; color:white; border-radius:12px; z-index:9999;`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

window.traiterDemande = traiterDemande;
window.soumettreTraitement = soumettreTraitement;
window.goToPage = goToPage;
window.closeModal = closeModal;