/**
 * ADMIN ÉTAT CIVIL - Gestion complète des demandes
 */

let currentPage = 1;
let currentFilters = {};
let currentDemande = null;

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadDemandes();
    initFilters();
    initEventListeners();
});

function initEventListeners() {
    // Filtres
    document.getElementById('applyFilters')?.addEventListener('click', () => {
        currentFilters = {
            type: document.getElementById('filterType').value,
            statut: document.getElementById('filterStatut').value,
            date_debut: document.getElementById('filterDateDebut').value,
            date_fin: document.getElementById('filterDateFin').value
        };
        currentPage = 1;
        loadDemandes();
    });

    // Recherche
    document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            currentFilters.search = e.target.value;
            loadDemandes();
        }
    });
}

async function loadStats() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
        const response = await fetch('http://localhost:8000/api/etat-civil/demandes/stats/', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const stats = await response.json();
        
        document.getElementById('statEnAttente').textContent = stats.en_attente || 0;
        document.getElementById('statEnCours').textContent = stats.en_cours || 0;
        document.getElementById('statValidees').textContent = stats.valide_agent || 0;
        document.getElementById('statRejetees').textContent = stats.rejete || 0;
        document.getElementById('statTotal').textContent = stats.total || 0;
    } catch (error) {
        console.error('Erreur chargement stats:', error);
        showNotification('Erreur chargement statistiques', 'error');
    }
}

async function loadDemandes() {
    const token = localStorage.getItem('access_token');
    const container = document.getElementById('demandesList');
    if (!container) return;
    
    container.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement des demandes...</p></div>';
    
    try {
        let url = `http://localhost:8000/api/etat-civil/demandes/?page=${currentPage}&page_size=10`;
        if (currentFilters.type) url += `&type_acte=${currentFilters.type}`;
        if (currentFilters.statut) url += `&statut=${currentFilters.statut}`;
        if (currentFilters.date_debut) url += `&date_debut=${currentFilters.date_debut}`;
        if (currentFilters.date_fin) url += `&date_fin=${currentFilters.date_fin}`;
        if (currentFilters.search) url += `&search=${currentFilters.search}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            displayDemandes(data.results);
            displayPagination(data.count);
        } else {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>Aucune demande trouvée</p></div>';
        }
    } catch (error) {
        console.error('Erreur:', error);
        container.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Erreur de chargement</p></div>';
    }
}

function displayDemandes(demandes) {
    const container = document.getElementById('demandesList');
    container.innerHTML = '';
    
    demandes.forEach(demande => {
        const item = document.createElement('div');
        item.className = 'demande-item';
        item.style.borderLeftColor = getStatutCouleur(demande.statut);
        
        const typeLabel = {
            'naissance': 'Acte de naissance', 'mariage': 'Acte de mariage',
            'deces': 'Acte de décès', 'reconnaissance': 'Reconnaissance',
            'adoption': 'Adoption'
        }[demande.type_acte] || demande.type_acte;
        
        item.innerHTML = `
            <div class="demande-header">
                <div class="demande-statut ${getStatutClass(demande.statut)}">
                    <i class="fas ${getStatutIcon(demande.statut)}"></i> ${getStatutTexte(demande.statut)}
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
                <button class="btn-download" onclick="ouvrirTraitement('${demande.id}')">
                    <i class="fas fa-edit"></i> Traiter
                </button>
                <button class="btn-preview" onclick="voirDetail('${demande.id}')">
                    <i class="fas fa-eye"></i> Détail
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
    html += `<button class="page-prev" ${currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${currentPage - 1})">&laquo;</button>`;
    
    for (let i = 1; i <= Math.min(totalPages, 5); i++) {
        html += `<button class="${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }
    
    if (totalPages > 5) html += `<span>...</span><button onclick="goToPage(${totalPages})">${totalPages}</button>`;
    
    html += `<button class="page-next" ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">&raquo;</button>`;
    
    pagination.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    loadDemandes();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function ouvrirTraitement(demandeId) {
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
        
        const typeLabel = {
            'naissance': 'Naissance', 'mariage': 'Mariage', 'deces': 'Décès',
            'reconnaissance': 'Reconnaissance', 'adoption': 'Adoption'
        }[demande.type_acte];
        
        modalBody.innerHTML = `
            <div class="detail-section">
                <h4>Demande n°${demande.reference}</h4>
                <p><strong>Type:</strong> ${typeLabel}</p>
                <p><strong>Demandeur:</strong> ${demande.demandeur_nom}</p>
                <p><strong>Date création:</strong> ${new Date(demande.date_creation).toLocaleString('fr-FR')}</p>
                <p><strong>Tarif:</strong> ${demande.tarif_calcule} FCFA</p>
            </div>
            <div class="form-group">
                <label>Action</label>
                <select id="actionSelect" class="filter-select">
                    <option value="valider">✅ Valider la demande</option>
                    <option value="rejeter">❌ Rejeter la demande</option>
                    <option value="en_cours">🔄 Marquer en cours</option>
                </select>
            </div>
            <div class="form-group">
                <label>Commentaire (obligatoire pour rejet)</label>
                <textarea id="commentaire" class="demande-textarea" rows="3" placeholder="Motif du rejet..."></textarea>
            </div>
            <div class="demande-actions" style="margin-top: 20px;">
                <button class="btn-primary" onclick="traiterDemande()">Confirmer</button>
                <button class="btn-cancel" onclick="closeModal()">Annuler</button>
            </div>
        `;
    } catch (error) {
        modalBody.innerHTML = '<div class="empty-state"><p>Erreur de chargement</p></div>';
    }
}

async function traiterDemande() {
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
            loadStats();
            loadDemandes();
        } else {
            showNotification('Erreur lors du traitement', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

async function voirDetail(demandeId) {
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
        
        modalBody.innerHTML = `
            <div class="detail-section">
                <h4>Détail complet</h4>
                <pre style="background:#f5f5f5; padding:16px; border-radius:12px; overflow-x:auto; font-size:12px;">${JSON.stringify(demande.data, null, 2)}</pre>
            </div>
            <button class="btn-primary" onclick="closeModal()">Fermer</button>
        `;
    } catch (error) {
        modalBody.innerHTML = '<div class="empty-state"><p>Erreur de chargement</p></div>';
    }
}

function initFilters() {
    const filterBtn = document.getElementById('applyFilters');
    if (filterBtn) filterBtn.onclick = () => {
        currentFilters = {
            type: document.getElementById('filterType')?.value || '',
            statut: document.getElementById('filterStatut')?.value || '',
            date_debut: document.getElementById('filterDateDebut')?.value || '',
            date_fin: document.getElementById('filterDateFin')?.value || ''
        };
        currentPage = 1;
        loadDemandes();
    };
}

function closeModal() {
    document.getElementById('traitementModal').classList.remove('active');
    currentDemande = null;
}

function getStatutCouleur(statut) {
    const couleurs = {
        'brouillon': '#6c757d', 'en_attente': '#f59e0b', 'en_cours': '#3b82f6',
        'valide_agent': '#10b981', 'valide_citoyen': '#8b5cf6', 'signe': '#06b6d4',
        'rejete': '#ef4444', 'delivre': '#10b981'
    };
    return couleurs[statut] || '#6c757d';
}

function getStatutClass(statut) { return `statut-${statut}`; }
function getStatutIcon(statut) { return statut.includes('valide') ? 'fa-check-circle' : statut === 'rejete' ? 'fa-times-circle' : 'fa-clock'; }
function getStatutTexte(statut) {
    const textes = {
        'brouillon': 'Brouillon', 'en_attente': 'En attente', 'en_cours': 'En cours',
        'valide_agent': 'Validé agent', 'valide_citoyen': 'Validé citoyen',
        'signe': 'Signé', 'rejete': 'Rejeté', 'delivre': 'Délivré'
    };
    return textes[statut] || statut;
}

function showNotification(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i> ${message}`;
    toast.style.cssText = `
        position: fixed; bottom: 20px; right: 20px; padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : '#ef4444'}; color: white;
        border-radius: 12px; z-index: 9999; animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

window.ouvrirTraitement = ouvrirTraitement;
window.voirDetail = voirDetail;
window.traiterDemande = traiterDemande;
window.goToPage = goToPage;
window.closeModal = closeModal;