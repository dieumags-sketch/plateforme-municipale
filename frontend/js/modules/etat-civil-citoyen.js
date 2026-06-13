/**
 * CITOYEN ÉTAT CIVIL - Suivi des demandes
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
    
    if (!token) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-lock"></i><p>Connectez-vous pour voir vos demandes</p><a href="../../accounts/login.html" class="btn-primary">Se connecter</a></div>';
        return;
    }
    
    container.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement...</p></div>';
    
    try {
        let url = `http://localhost:8000/api/etat-civil/demandes/?page=${currentPage}`;
        if (search) url += `&search=${search}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            displayDemandes(data.results);
            displayPagination(data.count);
        } else {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>Aucune demande effectuée</p><a href="../index.html" class="btn-primary">Faire une demande</a></div>';
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
                <span><i class="fas fa-calendar"></i> Créée le ${new Date(demande.date_creation).toLocaleDateString()}</span>
                <span><i class="fas fa-money-bill-wave"></i> ${demande.tarif_calcule || 0} FCFA</span>
            </div>
            <div class="demande-actions">
                <button class="btn-download" onclick="voirDetail('${demande.id}')">
                    <i class="fas fa-chart-line"></i> Suivre
                </button>
                ${demande.statut === 'valide_agent' ? '<button class="btn-payer" onclick="validerCitoyen(\'' + demande.id + '\')"><i class="fas fa-check-circle"></i> Valider mes infos</button>' : ''}
                ${demande.statut === 'signe' ? '<button class="btn-download" onclick="telechargerPDF(\'' + demande.id + '\')"><i class="fas fa-download"></i> Télécharger PDF</button>' : ''}
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

async function voirDetail(demandeId) {
    const token = localStorage.getItem('access_token');
    const modal = document.getElementById('detailModal');
    const modalBody = document.getElementById('modalBody');
    
    modalBody.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement...</p></div>';
    modal.classList.add('active');
    
    try {
        const response = await fetch(`http://localhost:8000/api/etat-civil/demandes/${demandeId}/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const demande = await response.json();
        currentDemande = demande;
        
        modalBody.innerHTML = `
            <div class="timeline" id="timeline"></div>
            <div class="detail-section">
                <h4>Informations</h4>
                <pre style="background:#f5f5f5; padding:16px; border-radius:12px; overflow-x:auto; font-size:12px;">${JSON.stringify(demande.data, null, 2)}</pre>
            </div>
            <button class="btn-primary" onclick="closeModal()">Fermer</button>
        `;
        
        // Afficher la timeline
        const timeline = document.getElementById('timeline');
        const etapes = [
            { statut: 'en_attente', label: 'Dépôt de la demande', date: demande.date_creation },
            { statut: 'valide_agent', label: 'Validation agent', date: demande.date_validation_agent },
            { statut: 'valide_citoyen', label: 'Validation citoyen', date: demande.date_validation_citoyen },
            { statut: 'signe', label: 'Signature électronique', date: demande.date_signature },
            { statut: 'delivre', label: 'Délivrance', date: demande.date_delivrance }
        ];
        
        let timelineHtml = '<div style="position:relative; padding:20px 0;">';
        let isCompleted = false;
        
        etapes.forEach((etape, index) => {
            const isActive = demande.statut === etape.statut;
            const isPast = Object.keys(etapes).some((_, i) => i <= index && demande.statut !== etape.statut);
            const status = demande.statut === etape.statut ? 'active' : (demande.date_validation_agent && etape.statut === 'valide_agent' ? 'completed' : 'pending');
            
            timelineHtml += `
                <div style="display:flex; margin-bottom:20px; position:relative;">
                    <div style="width:40px; height:40px; border-radius:50%; background:${status === 'completed' ? '#10b981' : status === 'active' ? '#667eea' : '#e5e7eb'}; display:flex; align-items:center; justify-content:center; margin-right:16px; color:white;">
                        <i class="fas ${status === 'completed' ? 'fa-check' : (index + 1)}"></i>
                    </div>
                    <div style="flex:1;">
                        <div style="font-weight:600;">${etape.label}</div>
                        <div style="font-size:12px; color:#6c757d;">${etape.date ? new Date(etape.date).toLocaleString('fr-FR') : 'En attente'}</div>
                    </div>
                </div>
            `;
        });
        timelineHtml += '</div>';
        timeline.innerHTML = timelineHtml;
        
    } catch (error) {
        modalBody.innerHTML = '<div class="empty-state"><p>Erreur de chargement</p></div>';
    }
}

async function validerCitoyen(demandeId) {
    const token = localStorage.getItem('access_token');
    showNotification('Validation en cours...', 'info');
    
    try {
        const response = await fetch(`http://localhost:8000/api/etat-civil/demandes/${demandeId}/valider_citoyen/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ valide: true })
        });
        
        if (response.ok) {
            showNotification('Informations validées avec succès !', 'success');
            loadDemandes();
        } else {
            showNotification('Erreur lors de la validation', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

async function telechargerPDF(demandeId) {
    const token = localStorage.getItem('access_token');
    showNotification('Préparation du PDF...', 'info');
    
    try {
        const response = await fetch(`http://localhost:8000/api/etat-civil/demandes/${demandeId}/pdf/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `acte_${demandeId}.pdf`;
            a.click();
            window.URL.revokeObjectURL(url);
            showNotification('PDF téléchargé', 'success');
        } else {
            showNotification('Erreur lors du téléchargement', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

function closeModal() {
    document.getElementById('detailModal').classList.remove('active');
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
    toast.style.cssText = `position:fixed; bottom:20px; right:20px; padding:12px 20px; background:${type === 'success' ? '#10b981' : '#ef4444'}; color:white; border-radius:12px; z-index:9999;`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

window.voirDetail = voirDetail;
window.validerCitoyen = validerCitoyen;
window.telechargerPDF = telechargerPDF;
window.goToPage = goToPage;
window.closeModal = closeModal;