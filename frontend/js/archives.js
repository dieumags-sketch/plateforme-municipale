
/**
 * MODULE ARCHIVES MUNICIPALES - VERSION COMPLÈTE
 * Compatible avec le nouveau design moderne
 */

// ============================================
// CONFIGURATION
// ============================================

const API_BASE_URL = 'http://localhost:8000/api';
let currentPage = 1;
let currentFilters = {};
let totalPages = 1;
let totalArchives = 0;
let currentArchiveId = null;

// ============================================
// INITIALISATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Module Archives chargé - Version moderne');
    
    // Initialiser la navigation mobile
    initMobileNav();
    
    // Charger les catégories
    loadCategories();
    
    // Charger les années
    loadYears();
    
    // Charger les archives
    loadArchives();
    
    // Initialiser les événements
    initEvents();
});

// Navigation mobile
function initMobileNav() {
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navToggle.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
    }
}

// ============================================
// ÉVÉNEMENTS
// ============================================

function initEvents() {
    // Recherche
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('searchInput');
    
    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            currentPage = 1;
            loadArchives();
        });
    }
    
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                currentPage = 1;
                loadArchives();
            }
        });
    }
    
    // Filtres
    const filters = ['categorieFilter', 'anneeDebutFilter', 'anneeFinFilter', 'accesFilter'];
    filters.forEach(filterId => {
        const filter = document.getElementById(filterId);
        if (filter) {
            filter.addEventListener('change', () => {
                currentPage = 1;
                loadArchives();
            });
        }
    });
    
    // Tabs
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            switchTab(tabId);
        });
    });
    
    // Fermeture des modales avec la touche Echap
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            closeDemandeModal();
        }
    });
    
    // Déconnexion
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            window.location.href = '../../index.html';
        });
    }
    
    // Charger les infos utilisateur
    loadUserInfo();
}

// ============================================
// CHARGEMENT DES DONNÉES
// ============================================

async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE_URL}/archives/categories/`);
        const categories = await response.json();
        
        const select = document.getElementById('categorieFilter');
        if (select && categories.length > 0) {
            categories.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.slug;
                option.textContent = cat.nom;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Erreur chargement catégories:', error);
    }
}

function loadYears() {
    const currentYear = new Date().getFullYear();
    const anneeDebut = document.getElementById('anneeDebutFilter');
    const anneeFin = document.getElementById('anneeFinFilter');
    
    if (anneeDebut && anneeFin) {
        for (let year = currentYear; year >= 1950; year--) {
            const option1 = document.createElement('option');
            option1.value = year;
            option1.textContent = year;
            anneeDebut.appendChild(option1);
            
            const option2 = document.createElement('option');
            option2.value = year;
            option2.textContent = year;
            anneeFin.appendChild(option2);
        }
    }
}

function loadUserInfo() {
    const userStr = localStorage.getItem('user');
    const userNameSpan = document.getElementById('userName');
    
    if (userStr && userNameSpan) {
        const user = JSON.parse(userStr);
        userNameSpan.textContent = `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username || 'Citoyen';
    } else if (userNameSpan) {
        userNameSpan.textContent = 'Invité';
    }
}

async function loadArchives() {
    const grid = document.getElementById('archivesGrid');
    if (!grid) return;
    
    grid.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement des archives...</p></div>';
    
    try {
        // Construire l'URL avec les filtres
        let url = `${API_BASE_URL}/archives/archives/?page=${currentPage}&page_size=9`;
        
        const searchInput = document.getElementById('searchInput');
        if (searchInput && searchInput.value) {
            url += `&q=${encodeURIComponent(searchInput.value)}`;
        }
        
        const categorieFilter = document.getElementById('categorieFilter');
        if (categorieFilter && categorieFilter.value) {
            url += `&categorie=${categorieFilter.value}`;
        }
        
        const anneeDebut = document.getElementById('anneeDebutFilter');
        if (anneeDebut && anneeDebut.value) {
            url += `&annee_debut=${anneeDebut.value}`;
        }
        
        const anneeFin = document.getElementById('anneeFinFilter');
        if (anneeFin && anneeFin.value) {
            url += `&annee_fin=${anneeFin.value}`;
        }
        
        const accesFilter = document.getElementById('accesFilter');
        if (accesFilter && accesFilter.value) {
            url += `&niveau_acces=${accesFilter.value}`;
        }
        
        console.log('Chargement:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        
        totalArchives = data.count || 0;
        updateStatsBar();
        
        if (data.results && data.results.length > 0) {
            displayArchives(data.results);
            displayPagination(data.count);
        } else {
            grid.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-archive"></i>
                    <p>Aucune archive trouvée</p>
                    <small>Essayez d'autres critères de recherche</small>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erreur chargement:', error);
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Erreur de chargement des archives</p>
                <small>Vérifiez que le serveur Django est démarré sur le port 8000</small>
            </div>
        `;
    }
}

function updateStatsBar() {
    const totalSpan = document.getElementById('totalCount');
    if (totalSpan) {
        totalSpan.textContent = totalArchives;
    }
}

// ============================================
// AFFICHAGE DES ARCHIVES
// ============================================

function displayArchives(archives) {
    const grid = document.getElementById('archivesGrid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    archives.forEach(archive => {
        const card = document.createElement('div');
        card.className = 'archive-card';
        card.onclick = () => showArchiveDetail(archive.id);
        
        // Déterminer la classe du badge
        let badgeClass = 'badge-public';
        let badgeText = 'Accès libre';
        
        switch (archive.niveau_acces) {
            case 'restreint':
                badgeClass = 'badge-restreint';
                badgeText = 'Sur demande';
                break;
            case 'confidentiel':
                badgeClass = 'badge-confidentiel';
                badgeText = 'Confidentiel';
                break;
            case 'tres_confidentiel':
                badgeClass = 'badge-confidentiel';
                badgeText = 'Très confidentiel';
                break;
        }
        
        const prixText = archive.tarif_consultation > 0 ? `${archive.tarif_consultation.toLocaleString()} FCFA` : 'Gratuit';
        const dateText = archive.date_document ? new Date(archive.date_document).getFullYear() : 'N/A';
        
        card.innerHTML = `
            <div class="archive-vignette" style="background-image: url('${archive.vignette || 'https://placehold.co/400x200/667eea/white?text=Archive'}')">
                <span class="archive-badge ${badgeClass}">${badgeText}</span>
            </div>
            <div class="archive-content">
                <div class="archive-reference">${escapeHtml(archive.reference || 'N/A')}</div>
                <div class="archive-titre">${escapeHtml(archive.titre || 'Sans titre')}</div>
                <div class="archive-description">${escapeHtml(archive.description ? archive.description.substring(0, 120) : '')}...</div>
                <div class="archive-meta">
                    <span><i class="far fa-calendar-alt"></i> ${dateText}</span>
                    <span><i class="far fa-eye"></i> ${archive.vues || 0} vues</span>
                    <span class="archive-price">${prixText}</span>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function displayPagination(total) {
    const pagination = document.getElementById('pagination');
    if (!pagination) return;
    
    const perPage = 9;
    totalPages = Math.ceil(total / perPage);
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let paginationHtml = '';
    
    // Bouton précédent
    paginationHtml += `<button class="page-prev" ${currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${currentPage - 1})">&laquo;</button>`;
    
    // Numéros de page
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
        paginationHtml += `<button onclick="goToPage(1)">1</button>`;
        if (startPage > 2) paginationHtml += `<span class="pagination-dots">...</span>`;
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHtml += `<button class="${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) paginationHtml += `<span class="pagination-dots">...</span>`;
        paginationHtml += `<button onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }
    
    // Bouton suivant
    paginationHtml += `<button class="page-next" ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})">&raquo;</button>`;
    
    pagination.innerHTML = paginationHtml;
}

function goToPage(page) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    loadArchives();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============================================
// DÉTAIL D'UNE ARCHIVE
// ============================================

async function showArchiveDetail(archiveId) {
    console.log('Chargement du détail:', archiveId);
    
    const modal = document.getElementById('archiveModal');
    const modalBody = document.getElementById('modalBody');
    
    if (!modal || !modalBody) return;
    
    modalBody.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement...</p></div>';
    modal.classList.add('active');
    
    try {
        const response = await fetch(`${API_BASE_URL}/archives/archives/${archiveId}/`);
        const archive = await response.json();
        
        currentArchiveId = archive.id;
        
        modalBody.innerHTML = `
            <div class="detail-section">
                <h4><i class="fas fa-info-circle"></i> Informations générales</h4>
                <div class="detail-row">
                    <div class="detail-label">Référence :</div>
                    <div class="detail-value">${escapeHtml(archive.reference)}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Titre :</div>
                    <div class="detail-value">${escapeHtml(archive.titre)}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Catégorie :</div>
                    <div class="detail-value">${archive.categorie?.nom || '-'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Date :</div>
                    <div class="detail-value">${new Date(archive.date_document).toLocaleDateString('fr-FR')}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Auteur :</div>
                    <div class="detail-value">${escapeHtml(archive.auteur || '-')}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Description :</div>
                    <div class="detail-value">${escapeHtml(archive.description)}</div>
                </div>
            </div>
            
            <div class="detail-section">
                <h4><i class="fas fa-tag"></i> Mots-clés</h4>
                <div class="detail-value">
                    ${archive.mots_cles ? archive.mots_cles.split(',').map(tag => `<span class="tag">${tag.trim()}</span>`).join('') : '-'}
                </div>
            </div>
            
            <div class="detail-section">
                <h4><i class="fas fa-credit-card"></i> Tarifs d'accès</h4>
                <div class="tarif-cards" id="tarifCards">
                    <div class="tarif-card" data-type="consultation" data-price="${archive.tarif_consultation || 0}">
                        <i class="fas fa-eye"></i>
                        <div>Consultation sur place</div>
                        <div class="price">${(archive.tarif_consultation || 0).toLocaleString()} FCFA</div>
                    </div>
                    <div class="tarif-card" data-type="copie" data-price="${archive.tarif_copie || 0}">
                        <i class="fas fa-copy"></i>
                        <div>Copie numérique</div>
                        <div class="price">${(archive.tarif_copie || 0).toLocaleString()} FCFA</div>
                    </div>
                    <div class="tarif-card" data-type="impression" data-price="${archive.tarif_impression || 0}">
                        <i class="fas fa-print"></i>
                        <div>Impression papier</div>
                        <div class="price">${(archive.tarif_impression || 0).toLocaleString()} FCFA</div>
                    </div>
                    <div class="tarif-card" data-type="envoi" data-price="${archive.tarif_envoi || 0}">
                        <i class="fas fa-envelope"></i>
                        <div>Envoi par courrier</div>
                        <div class="price">${(archive.tarif_envoi || 0).toLocaleString()} FCFA</div>
                    </div>
                </div>
            </div>
            
            <div class="demande-form">
                <h4><i class="fas fa-paper-plane"></i> Demander l'accès</h4>
                <div class="form-group">
                    <label>Type de demande *</label>
                    <select id="demandeType" class="demande-select">
                        <option value="consultation">Consultation sur place - ${(archive.tarif_consultation || 0).toLocaleString()} FCFA</option>
                        <option value="copie">Copie numérique - ${(archive.tarif_copie || 0).toLocaleString()} FCFA</option>
                        <option value="impression">Impression papier - ${(archive.tarif_impression || 0).toLocaleString()} FCFA</option>
                        <option value="envoi">Envoi par courrier - ${(archive.tarif_envoi || 0).toLocaleString()} FCFA</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Motif de la demande *</label>
                    <textarea id="demandeMotif" class="demande-textarea" placeholder="Expliquez la raison de votre demande..."></textarea>
                </div>
                <div id="adresseGroup" class="form-group" style="display: none;">
                    <label>Adresse de livraison *</label>
                    <textarea id="demandeAdresse" class="demande-textarea" placeholder="Votre adresse complète..."></textarea>
                </div>
                <div class="form-group">
                    <label>Pièce justificative (optionnel)</label>
                    <input type="file" id="demandeJustificatif" accept=".pdf,.jpg,.png">
                </div>
                <button class="btn-primary" onclick="submitDemande('${archive.id}')">
                    <i class="fas fa-paper-plane"></i> Envoyer la demande
                </button>
            </div>
        `;
        
        // Gérer l'affichage du champ adresse
        const demandeType = document.getElementById('demandeType');
        if (demandeType) {
            demandeType.addEventListener('change', (e) => {
                const adresseGroup = document.getElementById('adresseGroup');
                adresseGroup.style.display = e.target.value === 'envoi' ? 'block' : 'none';
            });
        }
        
        // Gérer la sélection des cartes tarifaires
        const tarifCards = document.querySelectorAll('.tarif-card');
        tarifCards.forEach(card => {
            card.addEventListener('click', () => {
                tarifCards.forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                const type = card.dataset.type;
                const select = document.getElementById('demandeType');
                if (select) {
                    for (let i = 0; i < select.options.length; i++) {
                        if (select.options[i].value === type) {
                            select.selectedIndex = i;
                            break;
                        }
                    }
                }
                const adresseGroup = document.getElementById('adresseGroup');
                adresseGroup.style.display = type === 'envoi' ? 'block' : 'none';
            });
        });
        
        // Incrémenter les vues
        fetch(`${API_BASE_URL}/archives/archives/${archive.id}/incrementer_vues/`, { method: 'POST' });
        
    } catch (error) {
        console.error('Erreur:', error);
        modalBody.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Erreur de chargement du détail</p>
                <button class="btn-primary" onclick="closeModal()">Fermer</button>
            </div>
        `;
    }
}

// ============================================
// DEMANDE D'ACCÈS
// ============================================

async function submitDemande(archiveId) {
    const type = document.getElementById('demandeType')?.value;
    const motif = document.getElementById('demandeMotif')?.value;
    const adresse = document.getElementById('demandeAdresse')?.value || '';
    
    if (!motif) {
        showNotification('Veuillez indiquer le motif de votre demande', 'error');
        return;
    }
    
    if (type === 'envoi' && !adresse) {
        showNotification('Veuillez indiquer votre adresse de livraison', 'error');
        return;
    }
    
    const token = localStorage.getItem('access_token');
    if (!token) {
        showNotification('Veuillez vous connecter pour effectuer une demande', 'error');
        setTimeout(() => {
            window.location.href = '../../pages/accounts/login.html';
        }, 2000);
        return;
    }
    
    showNotification('Envoi de la demande en cours...', 'info');
    
    try {
        const response = await fetch(`${API_BASE_URL}/archives/archives/${archiveId}/demander_acces/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                archive_id: archiveId,
                type_demande: type,
                motif: motif,
                adresse_livraison: adresse
            })
        });
        
        if (response.ok) {
            showNotification('Demande envoyée avec succès ! Vous recevrez une notification sous 48h.', 'success');
            closeModal();
            
            // Basculer vers l'onglet "Mes demandes"
            const mesDemandesTab = document.querySelector('.tab-btn[data-tab="mes-demandes"]');
            if (mesDemandesTab) {
                mesDemandesTab.click();
            }
        } else {
            const error = await response.json();
            showNotification(error.error || 'Erreur lors de l\'envoi', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('Erreur de connexion au serveur', 'error');
    }
}

// ============================================
// MES DEMANDES
// ============================================

async function loadMesDemandes() {
    const container = document.getElementById('demandesList');
    if (!container) return;
    
    const token = localStorage.getItem('access_token');
    if (!token) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-lock"></i>
                <p>Connectez-vous pour voir vos demandes</p>
                <a href="../../pages/accounts/login.html" class="btn-primary">Se connecter</a>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>Chargement de vos demandes...</p></div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/archives/demandes/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const demandes = await response.json();
        
        if (demandes.length > 0) {
            displayDemandes(demandes);
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>Aucune demande effectuée</p>
                    <small>Faites une demande d'accès depuis l'onglet "Recherche"</small>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erreur:', error);
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Erreur de chargement des demandes</p>
                <small>Veuillez réessayer plus tard</small>
            </div>
        `;
    }
}

function displayDemandes(demandes) {
    const container = document.getElementById('demandesList');
    if (!container) return;
    
    container.innerHTML = '';
    
    demandes.forEach(demande => {
        const statutInfo = getStatutInfo(demande.statut);
        const date = new Date(demande.date_demande).toLocaleDateString('fr-FR');
        
        const demandeCard = document.createElement('div');
        demandeCard.className = 'demande-item';
        demandeCard.innerHTML = `
            <div class="demande-header">
                <div class="demande-statut ${statutInfo.class}">
                    <i class="fas ${statutInfo.icon}"></i> ${statutInfo.text}
                </div>
                <div class="demande-date"><i class="far fa-calendar-alt"></i> ${date}</div>
            </div>
            <div class="archive-reference">${escapeHtml(demande.archive_reference)}</div>
            <div class="archive-titre">${escapeHtml(demande.archive_titre)}</div>
            <div class="demande-details">
                <span><i class="fas fa-tag"></i> ${getTypeTexte(demande.type_demande)}</span>
                <span><i class="fas fa-money-bill-wave"></i> ${demande.montant_calcule.toLocaleString()} FCFA</span>
            </div>
            ${demande.commentaire_moderation ? `<div class="demande-commentaire"><i class="fas fa-comment"></i> ${escapeHtml(demande.commentaire_moderation)}</div>` : ''}
            <div class="demande-actions">
                ${demande.statut === 'valide' ? `<button class="btn-payer" onclick="payerDemande('${demande.id}', ${demande.montant_calcule})"><i class="fas fa-credit-card"></i> Payer ${demande.montant_calcule.toLocaleString()} FCFA</button>` : ''}
                ${demande.statut === 'paye' ? `<button class="btn-download" onclick="telechargerDocument('${demande.id}')"><i class="fas fa-download"></i> Télécharger</button>` : ''}
                ${demande.statut === 'en_attente' ? `<button class="btn-cancel" onclick="annulerDemande('${demande.id}')"><i class="fas fa-times"></i> Annuler</button>` : ''}
            </div>
        `;
        container.appendChild(demandeCard);
    });
}

function getStatutInfo(statut) {
    const infos = {
        'en_attente': { class: 'statut-en_attente', text: 'En attente de validation', icon: 'fa-clock' },
        'en_cours': { class: 'statut-en_cours', text: 'En cours de traitement', icon: 'fa-spinner' },
        'valide': { class: 'statut-valide', text: 'Validée - En attente de paiement', icon: 'fa-check-circle' },
        'paye': { class: 'statut-paye', text: 'Payée - Disponible', icon: 'fa-download' },
        'rejetee': { class: 'statut-rejetee', text: 'Rejetée', icon: 'fa-times-circle' },
        'livree': { class: 'statut-livree', text: 'Livrée', icon: 'fa-check-double' }
    };
    return infos[statut] || { class: 'statut-en_attente', text: statut, icon: 'fa-question' };
}

async function payerDemande(demandeId, montant) {
    if (confirm(`Confirmer le paiement de ${montant.toLocaleString()} FCFA ?`)) {
        showNotification('Traitement du paiement en cours...', 'info');
        
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`${API_BASE_URL}/archives/demandes/${demandeId}/effectuer_paiement/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                showNotification('Paiement effectué avec succès !', 'success');
                loadMesDemandes();
            } else {
                showNotification('Erreur lors du paiement', 'error');
            }
        } catch (error) {
            console.error('Erreur:', error);
            showNotification('Erreur de connexion', 'error');
        }
    }
}

async function telechargerDocument(demandeId) {
    showNotification('Préparation du téléchargement...', 'info');
    
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_BASE_URL}/archives/demandes/${demandeId}/telecharger/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `document_${demandeId}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            showNotification('Téléchargement terminé', 'success');
        } else {
            showNotification('Erreur lors du téléchargement', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

async function annulerDemande(demandeId) {
    if (confirm('Êtes-vous sûr de vouloir annuler cette demande ?')) {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`${API_BASE_URL}/archives/demandes/${demandeId}/annuler/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                showNotification('Demande annulée', 'success');
                loadMesDemandes();
            } else {
                showNotification('Erreur lors de l\'annulation', 'error');
            }
        } catch (error) {
            console.error('Erreur:', error);
            showNotification('Erreur de connexion', 'error');
        }
    }
}

// ============================================
// UTILITAIRES
// ============================================

function switchTab(tabId) {
    // Mettre à jour les boutons
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(btn => {
        if (btn.dataset.tab === tabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // Mettre à jour les contenus
    const contents = document.querySelectorAll('.tab-content');
    contents.forEach(content => {
        if (content.id === `${tabId}Tab`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
    
    // Charger les demandes si nécessaire
    if (tabId === 'mes-demandes') {
        loadMesDemandes();
    } else if (tabId === 'recherche') {
        loadArchives();
    }
}

function closeModal() {
    const modal = document.getElementById('archiveModal');
    if (modal) modal.classList.remove('active');
}

function closeDemandeModal() {
    const modal = document.getElementById('demandeModal');
    if (modal) modal.classList.remove('active');
}

function showNotification(message, type = 'info') {
    // Supprimer les anciennes notifications
    const oldToasts = document.querySelectorAll('.toast-notification');
    oldToasts.forEach(toast => toast.remove());
    
    // Créer une nouvelle notification
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
        <span>${message}</span>
    `;
    
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#667eea'};
        color: white;
        border-radius: 12px;
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 14px;
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

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getTypeTexte(type) {
    const types = {
        'consultation': 'Consultation sur place',
        'copie': 'Copie numérique',
        'impression': 'Impression papier',
        'envoi': 'Envoi par courrier'
    };
    return types[type] || type;
}

// Styles pour les notifications
const notificationStyle = document.createElement('style');
notificationStyle.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    .tag {
        display: inline-block;
        background: #f0f0f0;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        margin: 2px;
    }
    .pagination-dots {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        color: #6c757d;
    }
`;
document.head.appendChild(notificationStyle);

// Export global
window.goToPage = goToPage;
window.submitDemande = submitDemande;
window.payerDemande = payerDemande;
window.telechargerDocument = telechargerDocument;
window.annulerDemande = annulerDemande;
window.closeModal = closeModal;
window.closeDemandeModal = closeDemandeModal;