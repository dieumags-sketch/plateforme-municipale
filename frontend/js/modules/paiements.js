/**
 * MODULE PAIEMENTS - Script principal
 * Gestion des paiements, historique, et reçus
 */

const API_URL = 'http://localhost:8000/api/paiements';
let currentPage = 1;
let currentFilters = {};
let currentTransaction = null;
let selectedMode = null;

// ============================================
// INITIALISATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initModeSelection();
    initForm();
    
    // Si on est sur la page historique
    if (document.getElementById('transactionsList')) {
        loadStats();
        loadHistorique();
        initFilters();
    }
    
    // Si on est sur la page de paiement avec montant prérempli
    const urlParams = new URLSearchParams(window.location.search);
    const montant = urlParams.get('montant');
    const moduleSource = urlParams.get('module');
    const sourceId = urlParams.get('ref');
    
    if (montant && document.getElementById('montant')) {
        document.getElementById('montant').value = montant;
        document.getElementById('montantDisplay').textContent = parseInt(montant).toLocaleString();
    }
    if (moduleSource && document.getElementById('moduleSource')) {
        document.getElementById('moduleSource').value = moduleSource;
    }
    if (sourceId && document.getElementById('sourceId')) {
        document.getElementById('sourceId').value = sourceId;
    }
});

// ============================================
// SÉLECTION DU MODE DE PAIEMENT
// ============================================

function initModeSelection() {
    const modeCards = document.querySelectorAll('.mode-card');
    modeCards.forEach(card => {
        card.addEventListener('click', () => {
            modeCards.forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            selectedMode = card.dataset.mode;
            updateForm(selectedMode);
        });
    });
}

function updateForm(mode) {
    const bankInfo = document.getElementById('bankInfo');
    const phoneInput = document.getElementById('phoneInput');
    const uploadSection = document.getElementById('uploadSection');
    const cashInfo = document.getElementById('cashInfo');
    
    if (bankInfo) bankInfo.style.display = mode === 'virement' ? 'block' : 'none';
    if (phoneInput) phoneInput.style.display = (mode === 'mtn' || mode === 'orange') ? 'flex' : 'none';
    if (uploadSection) uploadSection.style.display = mode === 'virement' ? 'block' : 'none';
    if (cashInfo) cashInfo.style.display = mode === 'cash' ? 'flex' : 'none';
    
    // Mettre à jour le récapitulatif
    updateRecap();
}

// ============================================
// FORMULAIRE DE PAIEMENT
// ============================================

function initForm() {
    const montantInput = document.getElementById('montant');
    if (montantInput) {
        montantInput.addEventListener('input', () => {
            const montant = parseFloat(montantInput.value) || 0;
            document.getElementById('montantDisplay').textContent = montant.toLocaleString();
            updateRecap();
        });
    }
    
    const form = document.getElementById('paiementForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await initierPaiement();
        });
    }
}

function updateRecap() {
    const montant = parseFloat(document.getElementById('montant')?.value) || 0;
    const mode = selectedMode;
    
    if (!mode || montant === 0) {
        document.getElementById('recapSection').style.display = 'none';
        return;
    }
    
    let frais = 0;
    if (mode === 'mtn' || mode === 'orange') {
        if (montant <= 1000) frais = 0;
        else if (montant <= 5000) frais = 50;
        else if (montant <= 10000) frais = 100;
        else frais = montant * 0.01;
    }
    
    const total = montant + frais;
    
    document.getElementById('recapNet').textContent = `${montant.toLocaleString()} FCFA`;
    document.getElementById('recapFrais').textContent = `${frais.toLocaleString()} FCFA`;
    document.getElementById('recapTotal').textContent = `${total.toLocaleString()} FCFA`;
    document.getElementById('recapSection').style.display = 'block';
}

async function initierPaiement() {
    if (!selectedMode) {
        showNotification('Veuillez choisir un mode de paiement', 'error');
        return;
    }
    
    const montant = parseFloat(document.getElementById('montant').value);
    const telephone = document.getElementById('telephone')?.value;
    const moduleSource = document.getElementById('moduleSource')?.value;
    const sourceId = document.getElementById('sourceId')?.value || '';
    const description = document.getElementById('description')?.value || '';
    
    if (!montant || montant <= 0) {
        showNotification('Montant invalide', 'error');
        return;
    }
    
    if ((selectedMode === 'mtn' || selectedMode === 'orange') && !telephone) {
        showNotification('Numéro de téléphone requis', 'error');
        return;
    }
    
    if (!moduleSource) {
        showNotification('Veuillez sélectionner un service', 'error');
        return;
    }
    
    const token = localStorage.getItem('access_token');
    if (!token) {
        showNotification('Veuillez vous connecter', 'error');
        setTimeout(() => window.location.href = '../accounts/login.html', 2000);
        return;
    }
    
    showNotification('Initialisation du paiement...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/transactions/initier/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                montant: montant,
                mode: selectedMode,
                telephone: telephone,
                module_source: moduleSource,
                source_id: sourceId,
                description: description
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (data.code_envoye) {
                currentTransaction = { reference: data.reference, montant: data.montant_total };
                showCodeModal(data.reference, telephone);
            } else if (selectedMode === 'virement') {
                showNotification('Virement initié. Envoyez la preuve.', 'success');
                document.getElementById('uploadSection').style.display = 'block';
            } else if (selectedMode === 'cash') {
                showNotification('Paiement enregistré. Présentez-vous en mairie.', 'success');
                setTimeout(() => window.location.href = 'historique.html', 2000);
            } else {
                showNotification('Paiement initialisé avec succès', 'success');
                setTimeout(() => window.location.href = 'historique.html', 2000);
            }
        } else {
            showNotification(data.error || 'Erreur lors du paiement', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// ============================================
// MODAL CODE DE VALIDATION
// ============================================

let codeTimerInterval = null;
let remainingSeconds = 120;

function showCodeModal(reference, telephone) {
    const modal = document.getElementById('codeModal');
    const codePhone = document.getElementById('codePhone');
    if (codePhone) codePhone.textContent = telephone;
    
    modal.classList.add('active');
    startCodeTimer();
}

function startCodeTimer() {
    remainingSeconds = 120;
    updateTimerDisplay();
    
    if (codeTimerInterval) clearInterval(codeTimerInterval);
    codeTimerInterval = setInterval(() => {
        remainingSeconds--;
        updateTimerDisplay();
        
        if (remainingSeconds <= 0) {
            clearInterval(codeTimerInterval);
            document.getElementById('codeTimer').innerHTML = '<span style="color: #ef4444;">Code expiré</span>';
        }
    }, 1000);
}

function updateTimerDisplay() {
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = remainingSeconds % 60;
    document.getElementById('codeTimer').innerHTML = `Le code expire dans ${minutes}:${seconds.toString().padStart(2, '0')}`;
}

async function confirmerCode() {
    const code = document.getElementById('validationCode').value;
    if (!code || code.length !== 6) {
        showNotification('Code à 6 chiffres requis', 'error');
        return;
    }
    
    showNotification('Confirmation en cours...', 'info');
    
    const token = localStorage.getItem('access_token');
    
    try {
        const response = await fetch(`${API_URL}/transactions/confirmer/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                reference: currentTransaction?.reference,
                code: code
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Paiement confirmé avec succès !', 'success');
            closeCodeModal();
            setTimeout(() => window.location.href = 'historique.html', 2000);
        } else {
            showNotification(data.error || 'Code invalide', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

async function renvoyerCode() {
    if (!currentTransaction) return;
    
    showNotification('Nouveau code envoyé', 'info');
    startCodeTimer();
}

function closeCodeModal() {
    const modal = document.getElementById('codeModal');
    if (modal) modal.classList.remove('active');
    if (codeTimerInterval) clearInterval(codeTimerInterval);
    document.getElementById('validationCode').value = '';
}

// ============================================
// HISTORIQUE DES PAIEMENTS
// ============================================

async function loadStats() {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    try {
        const response = await fetch(`${API_URL}/transactions/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.results) {
            let totalPaye = 0;
            let confirmees = 0;
            let enAttente = 0;
            
            data.results.forEach(t => {
                if (t.statut === 'confirme') {
                    totalPaye += t.montant_total;
                    confirmees++;
                } else if (t.statut === 'en_attente') {
                    enAttente++;
                }
            });
            
            document.getElementById('totalPaye').textContent = `${totalPaye.toLocaleString()} FCFA`;
            document.getElementById('totalTransactions').textContent = data.count || data.results.length;
            document.getElementById('totalConfirmees').textContent = confirmees;
            document.getElementById('totalEnAttente').textContent = enAttente;
        }
    } catch (error) {
        console.error('Erreur stats:', error);
    }
}

async function loadHistorique() {
    const token = localStorage.getItem('access_token');
    const container = document.getElementById('transactionsList');
    if (!container || !token) return;
    
    container.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement...</p></div>';
    
    try {
        let url = `${API_URL}/transactions/?page=${currentPage}`;
        if (currentFilters.periode && currentFilters.periode !== 'all') {
            url += `&periode=${currentFilters.periode}`;
        }
        if (currentFilters.statut && currentFilters.statut !== 'all') {
            url += `&statut=${currentFilters.statut}`;
        }
        if (currentFilters.mode && currentFilters.mode !== 'all') {
            url += `&mode=${currentFilters.mode}`;
        }
        if (currentFilters.search) {
            url += `&search=${currentFilters.search}`;
        }
        
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            displayHistorique(data.results);
            displayPagination(data.count);
        } else {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>Aucune transaction</p></div>';
        }
    } catch (error) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Erreur de chargement</p></div>';
    }
}

function displayHistorique(transactions) {
    const container = document.getElementById('transactionsList');
    container.innerHTML = '';
    
    transactions.forEach(transaction => {
        const item = document.createElement('div');
        item.className = 'transaction-item';
        item.style.borderLeftColor = getStatutCouleur(transaction.statut);
        
        const date = new Date(transaction.date_creation).toLocaleDateString('fr-FR');
        const time = new Date(transaction.date_creation).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        
        item.innerHTML = `
            <div class="transaction-info">
                <div class="reference">${transaction.reference}</div>
                <div class="montant">${transaction.montant_total.toLocaleString()} FCFA</div>
                <div class="date"><i class="far fa-calendar-alt"></i> ${date} à ${time}</div>
            </div>
            <div class="transaction-details">
                <span class="transaction-statut statut-${transaction.statut}">${transaction.statut_display}</span>
                <div class="mode">${transaction.mode_display}</div>
                ${transaction.statut === 'confirme' ? `<button class="btn-download" onclick="voirDetail('${transaction.id}')"><i class="fas fa-eye"></i></button>` : ''}
                ${transaction.statut === 'confirme' ? `<button class="btn-download" onclick="telechargerRecu('${transaction.id}')"><i class="fas fa-download"></i></button>` : ''}
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
    
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }
    
    if (endPage < totalPages) {
        html += `<span>...</span><button onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }
    
    html += `<button class="page-next" ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">&raquo;</button>`;
    pagination.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    loadHistorique();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function initFilters() {
    document.getElementById('applyFilters')?.addEventListener('click', () => {
        currentFilters = {
            periode: document.getElementById('periodeFilter').value,
            statut: document.getElementById('statutFilter').value,
            mode: document.getElementById('modeFilter').value,
            search: document.getElementById('searchInput').value
        };
        currentPage = 1;
        loadHistorique();
        loadStats();
    });
}

function resetFilters() {
    document.getElementById('periodeFilter').value = 'all';
    document.getElementById('statutFilter').value = 'all';
    document.getElementById('modeFilter').value = 'all';
    document.getElementById('searchInput').value = '';
    currentFilters = {};
    currentPage = 1;
    loadHistorique();
    loadStats();
}

// ============================================
// DÉTAIL TRANSACTION
// ============================================

async function voirDetail(transactionId) {
    const token = localStorage.getItem('access_token');
    const modal = document.getElementById('detailModal');
    const modalBody = document.getElementById('detailModalBody');
    
    if (!modal || !modalBody) return;
    
    modalBody.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement...</p></div>';
    modal.classList.add('active');
    
    try {
        const response = await fetch(`${API_URL}/transactions/${transactionId}/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const transaction = await response.json();
        
        modalBody.innerHTML = `
            <div class="detail-section">
                <h4>Transaction</h4>
                <div class="detail-row"><span class="detail-label">Référence:</span><span>${transaction.reference}</span></div>
                <div class="detail-row"><span class="detail-label">Date:</span><span>${new Date(transaction.date_creation).toLocaleString('fr-FR')}</span></div>
                <div class="detail-row"><span class="detail-label">Statut:</span><span class="statut-${transaction.statut}">${transaction.statut_display}</span></div>
            </div>
            <div class="detail-section">
                <h4>Montants</h4>
                <div class="detail-row"><span class="detail-label">Net:</span><span>${transaction.montant_net.toLocaleString()} FCFA</span></div>
                <div class="detail-row"><span class="detail-label">Frais:</span><span>${transaction.frais.toLocaleString()} FCFA</span></div>
                <div class="detail-row"><span class="detail-label">Taxe:</span><span>${transaction.taxe.toLocaleString()} FCFA</span></div>
                <div class="detail-row total"><span class="detail-label">Total:</span><span><strong>${transaction.montant_total.toLocaleString()} FCFA</strong></span></div>
            </div>
            <div class="detail-section">
                <h4>Paiement</h4>
                <div class="detail-row"><span class="detail-label">Mode:</span><span>${transaction.mode_display}</span></div>
                <div class="detail-row"><span class="detail-label">Téléphone:</span><span>${transaction.telephone || '-'}</span></div>
                <div class="detail-row"><span class="detail-label">Transaction ID:</span><span>${transaction.numero_transaction || '-'}</span></div>
            </div>
            <div class="detail-section">
                <h4>Service</h4>
                <div class="detail-row"><span class="detail-label">Module:</span><span>${transaction.module_source}</span></div>
                <div class="detail-row"><span class="detail-label">Référence:</span><span>${transaction.source_id || '-'}</span></div>
            </div>
            <button class="btn-primary" onclick="closeDetailModal()" style="width: 100%; margin-top: 20px;">Fermer</button>
        `;
    } catch (error) {
        modalBody.innerHTML = '<div class="empty-state">Erreur de chargement</div>';
    }
}

function closeDetailModal() {
    document.getElementById('detailModal').classList.remove('active');
}

async function telechargerRecu(transactionId) {
    const token = localStorage.getItem('access_token');
    showNotification('Préparation du reçu...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/transactions/${transactionId}/recu/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `recu_${transactionId}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            showNotification('Reçu téléchargé', 'success');
        } else {
            showNotification('Erreur lors du téléchargement', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

// ============================================
// UPLOAD PREUVE VIREMENT
// ============================================

const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('preuveVirement');

if (uploadArea && fileInput) {
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) handleFileUpload(file);
    });
    fileInput.addEventListener('change', (e) => {
        if (e.target.files[0]) handleFileUpload(e.target.files[0]);
    });
}

async function handleFileUpload(file) {
    const validTypes = ['image/jpeg', 'image/png', 'application/pdf'];
    if (!validTypes.includes(file.type)) {
        showNotification('Format non supporté (PDF, JPG, PNG)', 'error');
        return;
    }
    
    if (file.size > 5 * 1024 * 1024) {
        showNotification('Fichier trop volumineux (max 5Mo)', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('preuve_virement', file);
    formData.append('reference', currentTransaction?.reference || '');
    
    const token = localStorage.getItem('access_token');
    
    try {
        const response = await fetch(`${API_URL}/transactions/confirmer/`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        
        if (response.ok) {
            document.getElementById('fileName').textContent = file.name;
            showNotification('Preuve envoyée, en attente de validation', 'success');
        } else {
            showNotification('Erreur lors de l\'envoi', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

// ============================================
// UTILITAIRES
// ============================================

function getStatutCouleur(statut) {
    const couleurs = {
        'confirme': '#10b981',
        'en_attente': '#f59e0b',
        'initie': '#3b82f6',
        'echoue': '#ef4444',
        'annule': '#6c757d',
        'rembourse': '#8b5cf6'
    };
    return couleurs[statut] || '#6c757d';
}

function showNotification(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i> ${message}`;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 12px;
        z-index: 9999;
        animation: slideIn 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        font-family: 'Inter', sans-serif;
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Exports globaux pour les appels inline
window.goToPage = goToPage;
window.voirDetail = voirDetail;
window.telechargerRecu = telechargerRecu;
window.closeDetailModal = closeDetailModal;
window.confirmerCode = confirmerCode;
window.renvoyerCode = renvoyerCode;
window.closeCodeModal = closeCodeModal;
window.resetFilters = resetFilters;
window.applyFilters = () => {
    const applyBtn = document.getElementById('applyFilters');
    if (applyBtn) applyBtn.click();
};