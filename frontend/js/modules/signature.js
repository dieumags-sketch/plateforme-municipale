/**
 * MODULE SIGNATURE ÉLECTRONIQUE
 */

const API_URL = 'http://localhost:8000/api/signature-electronique';
let canvas = null;
let ctx = null;
let isDrawing = false;
let lastX = 0, lastY = 0;

// ============================================
// INITIALISATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initCanvas();
    initModeles();
    chargerCertificat();
    
    // Si on est sur la page de vérification
    const urlParams = new URLSearchParams(window.location.search);
    const signatureId = urlParams.get('id');
    if (signatureId && document.getElementById('verifierBtn')) {
        chargerSignatureInfo(signatureId);
    }
    
    // Si on est sur la page de signature par token
    const token = urlParams.get('token');
    if (token && document.getElementById('signerToken')) {
        chargerDemandeParToken(token);
    }
});

// ============================================
// CANVAS
// ============================================

function initCanvas() {
    const canvasElement = document.getElementById('signatureCanvas');
    if (!canvasElement) return;
    
    canvas = canvasElement;
    ctx = canvas.getContext('2d');
    
    canvas.width = canvas.offsetWidth;
    canvas.height = 150;
    
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#1a237e';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseleave', stopDrawing);
    
    canvas.addEventListener('touchstart', startDrawingTouch);
    canvas.addEventListener('touchmove', drawTouch);
    canvas.addEventListener('touchend', stopDrawing);
}

function startDrawing(e) {
    isDrawing = true;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    lastX = (e.clientX - rect.left) * scaleX;
    lastY = (e.clientY - rect.top) * scaleY;
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
}

function draw(e) {
    if (!isDrawing) return;
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const currentX = (e.clientX - rect.left) * scaleX;
    const currentY = (e.clientY - rect.top) * scaleY;
    ctx.lineTo(currentX, currentY);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(currentX, currentY);
    lastX = currentX;
    lastY = currentY;
}

function startDrawingTouch(e) {
    e.preventDefault();
    const touch = e.touches[0];
    isDrawing = true;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    lastX = (touch.clientX - rect.left) * scaleX;
    lastY = (touch.clientY - rect.top) * scaleY;
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
}

function drawTouch(e) {
    if (!isDrawing) return;
    e.preventDefault();
    const touch = e.touches[0];
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const currentX = (touch.clientX - rect.left) * scaleX;
    const currentY = (touch.clientY - rect.top) * scaleY;
    ctx.lineTo(currentX, currentY);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(currentX, currentY);
    lastX = currentX;
    lastY = currentY;
}

function stopDrawing() {
    isDrawing = false;
    ctx.beginPath();
}

function clearCanvas() {
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#1a237e';
}

function getSignatureImage() {
    return canvas.toDataURL('image/png');
}

// ============================================
// MODÈLES DE SIGNATURE
// ============================================

function initModeles() {
    const modeles = document.querySelectorAll('.modele-card');
    modeles.forEach(modele => {
        modele.addEventListener('click', () => {
            modeles.forEach(m => m.classList.remove('selected'));
            modele.classList.add('selected');
            appliquerModele(modele.dataset.modele);
        });
    });
}

function appliquerModele(modele) {
    clearCanvas();
    ctx.font = '24px "Brush Script MT", cursive';
    ctx.fillStyle = '#1a237e';
    
    if (modele === 'classique') {
        ctx.fillText('Signature', 50, 80);
    } else if (modele === 'elegant') {
        ctx.fillText('Sincerely', 50, 80);
    } else if (modele === 'officiel') {
        ctx.font = '20px "Times New Roman", serif';
        ctx.fillText('Approuvé', 50, 80);
    }
}

// ============================================
// CERTIFICAT
// ============================================

async function chargerCertificat() {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    const container = document.getElementById('certificatInfo');
    if (!container) return;
    
    try {
        const response = await fetch(`${API_URL}/certificats/mon_certificat/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.status === 404) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-certificate"></i>
                    <p>Vous n'avez pas encore de certificat numérique</p>
                    <button class="btn-primary" onclick="creerCertificat()">Créer mon certificat</button>
                </div>
            `;
            return;
        }
        
        const certificat = await response.json();
        const statusClass = certificat.est_valide && !certificat.est_expire ? 'valide' : 
                           certificat.est_expire ? 'expire' : 'revoque';
        const statusText = certificat.est_valide && !certificat.est_expire ? 'Valide' :
                          certificat.est_expire ? 'Expiré' : 'Révoqué';
        
        container.innerHTML = `
            <div class="form-section-title"><i class="fas fa-certificate"></i> Mon certificat numérique</div>
            <div class="detail-row"><span class="detail-label">Numéro:</span><span>${certificat.numero_serie}</span></div>
            <div class="detail-row"><span class="detail-label">Émis le:</span><span>${new Date(certificat.date_emission).toLocaleDateString('fr-FR')}</span></div>
            <div class="detail-row"><span class="detail-label">Expire le:</span><span>${new Date(certificat.date_expiration).toLocaleDateString('fr-FR')}</span></div>
            <div class="detail-row"><span class="detail-label">Niveau:</span><span>${certificat.niveau_display}</span></div>
            <div class="certificat-status status-${statusClass}">${statusText}</div>
        `;
        document.getElementById('creerCertificatBtn')?.remove();
    } catch (error) {
        console.error('Erreur:', error);
    }
}

async function creerCertificat() {
    const motDePasse = prompt('Choisissez un mot de passe pour votre certificat (minimum 8 caractères):');
    if (!motDePasse || motDePasse.length < 8) {
        showNotification('Mot de passe trop court', 'error');
        return;
    }
    
    const niveau = document.getElementById('niveauCertificat')?.value || 1;
    
    showNotification('Création du certificat...', 'info');
    
    const token = localStorage.getItem('access_token');
    
    try {
        const response = await fetch(`${API_URL}/certificats/creer/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                mot_de_passe: motDePasse,
                niveau_confiance: parseInt(niveau)
            })
        });
        
        if (response.ok) {
            showNotification('Certificat créé avec succès !', 'success');
            chargerCertificat();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Erreur', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

// ============================================
// SIGNATURE DE DOCUMENT
// ============================================

async function signerDocument() {
    const moduleSource = document.getElementById('moduleSource')?.value;
    const sourceId = document.getElementById('sourceId')?.value;
    const documentTitre = document.getElementById('documentTitre')?.value;
    const motDePasse = document.getElementById('motDePasse')?.value;
    const signatureImage = getSignatureImage();
    
    if (!moduleSource || !sourceId || !documentTitre) {
        showNotification('Veuillez remplir tous les champs', 'error');
        return;
    }
    
    if (!motDePasse) {
        showNotification('Mot de passe requis', 'error');
        return;
    }
    
    if (signatureImage === canvas.toDataURL()) {
        showNotification('Veuillez apposer votre signature', 'error');
        return;
    }
    
    const token = localStorage.getItem('access_token');
    if (!token) {
        showNotification('Veuillez vous connecter', 'error');
        window.location.href = '../accounts/login.html';
        return;
    }
    
    showNotification('Signature en cours...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/signatures/signer_document/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                module_source: moduleSource,
                source_id: sourceId,
                document_titre: documentTitre,
                document_contenu: signatureImage,
                signature_image: signatureImage,
                mot_de_passe: motDePasse
            })
        });
        
        if (response.ok) {
            showNotification('Document signé avec succès !', 'success');
            setTimeout(() => {
                window.location.href = 'historique.html';
            }, 2000);
        } else {
            const error = await response.json();
            showNotification(error.error || 'Erreur', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

// ============================================
// VÉRIFICATION DE SIGNATURE
// ============================================

async function chargerSignatureInfo(signatureId) {
    try {
        const response = await fetch(`${API_URL}/signatures/${signatureId}/`);
        const signature = await response.json();
        
        document.getElementById('signatureInfo').innerHTML = `
            <div class="detail-row"><span class="detail-label">Document:</span><span>${signature.document_titre}</span></div>
            <div class="detail-row"><span class="detail-label">Signataire:</span><span>${signature.signataire_nom}</span></div>
            <div class="detail-row"><span class="detail-label">Date:</span><span>${new Date(signature.timestamp_signature).toLocaleString('fr-FR')}</span></div>
            <div class="detail-row"><span class="detail-label">Module:</span><span>${signature.module_display}</span></div>
        `;
    } catch (error) {
        console.error('Erreur:', error);
    }
}

async function verifierSignature() {
    const signatureId = document.getElementById('signatureId')?.value;
    const documentContent = getSignatureImage();
    
    if (!signatureId) {
        showNotification('ID de signature requis', 'error');
        return;
    }
    
    showNotification('Vérification en cours...', 'info');
    
    const token = localStorage.getItem('access_token');
    
    try {
        const response = await fetch(`${API_URL}/signatures/verifier/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                signature_id: signatureId,
                document: documentContent
            })
        });
        
        const result = await response.json();
        const container = document.getElementById('verificationResult');
        container.style.display = 'block';
        container.className = `verification-result ${result.valide ? 'valide' : 'invalide'}`;
        
        if (result.valide) {
            container.innerHTML = `
                <i class="fas fa-check-circle"></i>
                <h3>Signature authentique</h3>
                <p>Ce document a été signé par ${result.details.signataire}</p>
                <p>Le ${new Date(result.details.date).toLocaleString('fr-FR')}</p>
                <div class="verification-details">
                    <h4>Détails du certificat</h4>
                    <p>Certificat: ${result.details.certificat}</p>
                </div>
            `;
        } else {
            container.innerHTML = `
                <i class="fas fa-times-circle"></i>
                <h3>Signature invalide</h3>
                <p>${result.message}</p>
            `;
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

// ============================================
// DEMANDE PAR TOKEN (signature externe)
// ============================================

async function chargerDemandeParToken(token) {
    try {
        const response = await fetch(`${API_URL}/demandes/?search=${token}`);
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            const demande = data.results[0];
            document.getElementById('demandeInfo').innerHTML = `
                <div class="detail-row"><span class="detail-label">Document:</span><span>${demande.document_titre}</span></div>
                <div class="detail-row"><span class="detail-label">De:</span><span>${demande.destinataire_nom || 'Administration'}</span></div>
                <div class="detail-row"><span class="detail-label">Expire le:</span><span>${new Date(demande.date_expiration).toLocaleDateString('fr-FR')}</span></div>
            `;
            document.getElementById('signerToken').dataset.token = token;
        }
    } catch (error) {
        console.error('Erreur:', error);
    }
}

async function signerAvecToken() {
    const token = document.getElementById('signerToken')?.dataset.token;
    const signatureImage = getSignatureImage();
    const niveau = document.getElementById('niveauSignature')?.value || 1;
    const motDePasse = document.getElementById('motDePasseToken')?.value;
    
    if (!signatureImage) {
        showNotification('Veuillez apposer votre signature', 'error');
        return;
    }
    
    if (!motDePasse) {
        showNotification('Mot de passe requis', 'error');
        return;
    }
    
    showNotification('Signature en cours...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/demandes/signer_token/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                token: token,
                signature_image: signatureImage,
                niveau_signature: parseInt(niveau),
                mot_de_passe: motDePasse
            })
        });
        
        if (response.ok) {
            showNotification('Document signé avec succès !', 'success');
            setTimeout(() => window.location.href = '../accounts/dashboard.html', 2000);
        } else {
            const error = await response.json();
            showNotification(error.error || 'Erreur', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

// ============================================
// HISTORIQUE
// ============================================

async function chargerHistorique() {
    const token = localStorage.getItem('access_token');
    const container = document.getElementById('historiqueList');
    if (!container || !token) return;
    
    container.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement...</p></div>';
    
    try {
        const response = await fetch(`${API_URL}/signatures/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            container.innerHTML = '';
            data.results.forEach(sig => {
                const item = document.createElement('div');
                item.className = 'demande-item';
                item.style.borderLeftColor = sig.est_valide ? '#10b981' : '#ef4444';
                item.innerHTML = `
                    <div class="demande-header">
                        <span class="demande-statut" style="background: ${sig.est_valide ? '#d1fae5' : '#fee2e2'}; color: ${sig.est_valide ? '#059669' : '#dc2626'}">
                            ${sig.est_valide ? '✓ Valide' : '✗ Invalide'}
                        </span>
                        <span>${new Date(sig.timestamp_signature).toLocaleDateString('fr-FR')}</span>
                    </div>
                    <div class="archive-titre">${sig.document_titre}</div>
                    <div class="demande-details">${sig.module_display}</div>
                `;
                container.appendChild(item);
            });
        } else {
            container.innerHTML = '<div class="empty-state">Aucune signature effectuée</div>';
        }
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Erreur de chargement</div>';
    }
}

// ============================================
// UTILITAIRES
// ============================================

function showNotification(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i> ${message}`;
    toast.style.cssText = `
        position: fixed; bottom: 20px; right: 20px; padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : '#ef4444'};
        color: white; border-radius: 12px; z-index: 9999;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

window.clearCanvas = clearCanvas;
window.creerCertificat = creerCertificat;
window.signerDocument = signerDocument;
window.verifierSignature = verifierSignature;
window.signerAvecToken = signerAvecToken;


// ============================================
// FONCTIONS COMPLÉMENTAIRES
// ============================================

// Gestion du niveau de signature
if (document.getElementById('niveauSignature')) {
    document.getElementById('niveauSignature').addEventListener('change', function() {
        const codePinGroup = document.getElementById('codePinGroup');
        if (codePinGroup) {
            codePinGroup.style.display = this.value >= 2 ? 'block' : 'none';
        }
    });
}

// Filtres sur la page historique
let currentPage = 1;
let currentFilters = {};

async function applyFilters() {
    currentFilters = {
        module: document.getElementById('moduleFilter')?.value || '',
        periode: document.getElementById('periodeFilter')?.value || '',
        statut: document.getElementById('statutFilter')?.value || ''
    };
    currentPage = 1;
    await chargerHistorique();
}

function resetFilters() {
    if (document.getElementById('moduleFilter')) document.getElementById('moduleFilter').value = '';
    if (document.getElementById('periodeFilter')) document.getElementById('periodeFilter').value = 'all';
    if (document.getElementById('statutFilter')) document.getElementById('statutFilter').value = 'all';
    currentFilters = {};
    currentPage = 1;
    chargerHistorique();
}

// Chargement de l'historique avec pagination
async function chargerHistorique() {
    const token = localStorage.getItem('access_token');
    const container = document.getElementById('historiqueList');
    if (!container || !token) return;
    
    container.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement...</p></div>';
    
    try {
        let url = `${API_URL}/signatures/?page=${currentPage}`;
        if (currentFilters.module) url += `&module_source=${currentFilters.module}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            displayHistorique(data.results);
            displayPagination(data.count);
        } else {
            container.innerHTML = '<div class="empty-state">Aucune signature effectuée</div>';
        }
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Erreur de chargement</div>';
    }
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
    if (totalPages > 5) {
        html += `<span>...</span><button onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }
    html += `<button class="page-next" ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">&raquo;</button>`;
    pagination.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    chargerHistorique();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function displayHistorique(signatures) {
    const container = document.getElementById('historiqueList');
    container.innerHTML = '';
    
    signatures.forEach(sig => {
        const item = document.createElement('div');
        item.className = 'demande-item';
        item.style.borderLeftColor = sig.est_valide ? '#10b981' : '#ef4444';
        item.innerHTML = `
            <div class="demande-header">
                <span class="demande-statut" style="background: ${sig.est_valide ? '#d1fae5' : '#fee2e2'}; color: ${sig.est_valide ? '#059669' : '#dc2626'}">
                    ${sig.est_valide ? '✓ Valide' : '✗ Invalide'}
                </span>
                <span>${new Date(sig.timestamp_signature).toLocaleDateString('fr-FR')}</span>
            </div>
            <div class="archive-titre">${sig.document_titre}</div>
            <div class="demande-details">
                <span><i class="fas fa-tag"></i> ${sig.module_display}</span>
                <span><i class="fas fa-user"></i> ${sig.signataire_nom}</span>
            </div>
            <div class="demande-actions">
                <button class="btn-download" onclick="voirDetailSignature('${sig.id}')"><i class="fas fa-eye"></i> Détail</button>
                <button class="btn-download" onclick="genererQRCodeSignature('${sig.id}')"><i class="fas fa-qrcode"></i> QR Code</button>
            </div>
        `;
        container.appendChild(item);
    });
}

async function voirDetailSignature(id) {
    const token = localStorage.getItem('access_token');
    const modal = document.getElementById('detailModal');
    const modalBody = document.getElementById('detailModalBody');
    
    if (!modal || !modalBody) return;
    
    modalBody.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement...</p></div>';
    modal.classList.add('active');
    
    try {
        const response = await fetch(`${API_URL}/signatures/${id}/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const sig = await response.json();
        
        modalBody.innerHTML = `
            <div class="detail-section">
                <h4>Document</h4>
                <div class="detail-row"><span class="detail-label">Titre:</span><span>${sig.document_titre}</span></div>
                <div class="detail-row"><span class="detail-label">Module:</span><span>${sig.module_display}</span></div>
                <div class="detail-row"><span class="detail-label">Référence:</span><span>${sig.source_id || '-'}</span></div>
            </div>
            <div class="detail-section">
                <h4>Signature</h4>
                <div class="detail-row"><span class="detail-label">Signataire:</span><span>${sig.signataire_nom}</span></div>
                <div class="detail-row"><span class="detail-label">Date:</span><span>${new Date(sig.timestamp_signature).toLocaleString('fr-FR')}</span></div>
                <div class="detail-row"><span class="detail-label">Statut:</span><span>${sig.est_valide ? 'Valide' : 'Invalide'}</span></div>
            </div>
            <div class="detail-section">
                <h4>Certificat</h4>
                <div class="detail-row"><span class="detail-label">Numéro:</span><span>${sig.certificat_info?.numero_serie || '-'}</span></div>
                <div class="detail-row"><span class="detail-label">Émis le:</span><span>${sig.certificat_info?.date_emission ? new Date(sig.certificat_info.date_emission).toLocaleDateString() : '-'}</span></div>
            </div>
            <button class="btn-primary" onclick="closeModal()" style="width: 100%; margin-top: 20px;">Fermer</button>
        `;
    } catch (error) {
        modalBody.innerHTML = '<div class="empty-state">Erreur de chargement</div>';
    }
}

function closeModal() {
    const modal = document.getElementById('detailModal');
    if (modal) modal.classList.remove('active');
}

async function genererQRCodeSignature(id) {
    const token = localStorage.getItem('access_token');
    try {
        const response = await fetch(`${API_URL}/signatures/${id}/qrcode/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        showNotification('QR code généré', 'success');
        window.open(data.qr_url, '_blank');
    } catch (error) {
        showNotification('Erreur', 'error');
    }
}

// Scanner QR code sur la page de vérification
if (document.getElementById('qr-reader')) {
    const html5QrCode = new Html5Qrcode("qr-reader");
    const qrConfig = { fps: 10, qrbox: { width: 250, height: 250 } };
    
    html5QrCode.start({ facingMode: "environment" }, qrConfig, (decodedText) => {
        const urlParams = new URLSearchParams(decodedText.split('?')[1]);
        const id = urlParams.get('id');
        if (id) {
            document.getElementById('signatureId').value = id;
            html5QrCode.stop();
            document.getElementById('qr-reader').innerHTML = '<p style="text-align:center;">QR code scanné !</p>';
            showNotification('QR code détecté', 'success');
        }
    }, (error) => {});
}

window.closeModal = closeModal;
window.voirDetailSignature = voirDetailSignature;
window.applyFilters = applyFilters;
window.resetFilters = resetFilters;
window.goToPage = goToPage;