// frontend/js/archives.js

// Configuration
const API_URL = 'http://localhost:8000/api/archives';
let currentPage = 1;
let currentFilters = {};

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    loadCategories();
    loadAnnees();
    loadArchives();
    
    // Événements
    document.getElementById('searchBtn').addEventListener('click', () => search());
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') search();
    });
    document.getElementById('categorieFilter').addEventListener('change', () => search());
    document.getElementById('anneeDebutFilter').addEventListener('change', () => search());
    document.getElementById('anneeFinFilter').addEventListener('change', () => search());
    document.getElementById('accesFilter').addEventListener('change', () => search());
    
    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab + 'Tab').classList.add('active');
            
            if (btn.dataset.tab === 'mes-demandes') {
                loadMesDemandes();
            }
        });
    });
});

// Charger les catégories
async function loadCategories() {
    try {
        const response = await fetch(`${API_URL}/archives/categories/`);
        const categories = await response.json();
        const select = document.getElementById('categorieFilter');
        categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.slug;
            option.textContent = cat.nom;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Erreur chargement catégories:', error);
    }
}

// Charger les années disponibles
async function loadAnnees() {
    const currentYear = new Date().getFullYear();
    const anneeDebut = document.getElementById('anneeDebutFilter');
    const anneeFin = document.getElementById('anneeFinFilter');
    
    for (let year = currentYear; year >= 1900; year--) {
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

// Rechercher des archives
async function search() {
    currentPage = 1;
    currentFilters = {
        q: document.getElementById('searchInput').value,
        categorie: document.getElementById('categorieFilter').value,
        annee_debut: document.getElementById('anneeDebutFilter').value,
        annee_fin: document.getElementById('anneeFinFilter').value,
        niveau_acces: document.getElementById('accesFilter').value
    };
    loadArchives();
}

// Charger les archives
async function loadArchives() {
    const grid = document.getElementById('archivesGrid');
    grid.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';
    
    try {
        let url = `${API_URL}/archives/?page=${currentPage}`;
        for (const [key, value] of Object.entries(currentFilters)) {
            if (value) url += `&${key}=${encodeURIComponent(value)}`;
        }
        
        const token = localStorage.getItem('access_token');
        const response = await fetch(url, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            renderArchives(data.results);
            renderPagination(data.count);
        } else {
            grid.innerHTML = '<div class="empty-state"><i class="fas fa-archive"></i><p>Aucune archive trouvée</p></div>';
        }
    } catch (error) {
        console.error('Erreur:', error);
        grid.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Erreur de chargement</p></div>';
    }
}

// Afficher les archives
function renderArchives(archives) {
    const grid = document.getElementById('archivesGrid');
    grid.innerHTML = '';
    
    archives.forEach(archive => {
        const card = document.createElement('div');
        card.className = 'archive-card';
        card.onclick = () => showArchiveDetail(archive.id);
        
        const badgeClass = archive.niveau_acces === 'public' ? 'badge-public' : 
                          (archive.niveau_acces === 'restreint' ? 'badge-restreint' : 'badge-confidentiel');
        const badgeText = archive.niveau_acces === 'public' ? 'Accès libre' :
                         (archive.niveau_acces === 'restreint' ? 'Sur demande' : 'Confidentiel');
        
        card.innerHTML = `
            <div class="archive-vignette" style="background-image: url('${archive.vignette || '../static/images/archive-default.jpg'}')">
                <span class="archive-badge ${badgeClass}">${badgeText}</span>
            </div>
            <div class="archive-content">
                <div class="archive-reference">${archive.reference}</div>
                <div class="archive-titre">${archive.titre}</div>
                <div class="archive-description">${archive.description?.substring(0, 100) || ''}...</div>
                <div class="archive-meta">
                    <span><i class="far fa-calendar-alt"></i> ${new Date(archive.date_document).getFullYear()}</span>
                    <span><i class="far fa-eye"></i> ${archive.vues} vues</span>
                    ${archive.tarif_consultation > 0 ? `<span class="archive-price">${archive.tarif_consultation} FCFA</span>` : '<span class="archive-price">Gratuit</span>'}
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

// Afficher le détail d'une archive
async function showArchiveDetail(archiveId) {
    const modal = document.getElementById('archiveModal');
    const modalBody = document.getElementById('modalBody');
    modalBody.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';
    modal.classList.add('active');
    
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/archives/${archiveId}/`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        const archive = await response.json();
        
        modalBody.innerHTML = `
            <div class="detail-section">
                <h4>Informations générales</h4>
                <div class="detail-row">
                    <div class="detail-label">Référence :</div>
                    <div class="detail-value">${archive.reference}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Titre :</div>
                    <div class="detail-value">${archive.titre}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Catégorie :</div>
                    <div class="detail-value">${archive.categorie?.nom || '-'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Date document :</div>
                    <div class="detail-value">${new Date(archive.date_document).toLocaleDateString('fr-FR')}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Auteur :</div>
                    <div class="detail-value">${archive.auteur || '-'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Description :</div>
                    <div class="detail-value">${archive.description}</div>
                </div>
            </div>
            
            <div class="detail-section">
                <h4>Accès et tarifs</h4>
                <div class="tarif-cards" id="tarifCards">
                    ${archive.tarif_consultation !== undefined ? `
                        <div class="tarif-card" data-type="consultation">
                            <i class="fas fa-eye"></i>
                            <div>Consultation sur place</div>
                            <div class="price">${archive.tarif_consultation} FCFA</div>
                        </div>
                    ` : ''}
                    ${archive.tarif_copie !== undefined ? `
                        <div class="tarif-card" data-type="copie">
                            <i class="fas fa-copy"></i>
                            <div>Copie numérique</div>
                            <div class="price">${archive.tarif_copie} FCFA</div>
                        </div>
                    ` : ''}
                    ${archive.tarif_impression !== undefined ? `
                        <div class="tarif-card" data-type="impression">
                            <i class="fas fa-print"></i>
                            <div>Impression papier</div>
                            <div class="price">${archive.tarif_impression} FCFA</div>
                        </div>
                    ` : ''}
                    ${archive.tarif_envoi !== undefined ? `
                        <div class="tarif-card" data-type="envoi">
                            <i class="fas fa-envelope"></i>
                            <div>Envoi par courrier</div>
                            <div class="price">${archive.tarif_envoi} FCFA</div>
                        </div>
                    ` : ''}
                </div>
            </div>
            
            <div class="demande-form">
                <h4>Faire une demande d'accès</h4>
                <div class="form-group">
                    <label>Type de demande *</label>
                    <select id="demandeType">
                        <option value="consultation">Consultation sur place</option>
                        <option value="copie">Copie numérique</option>
                        <option value="impression">Impression papier</option>
                        <option value="envoi">Envoi par courrier</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Motif de la demande *</label>
                    <textarea id="demandeMotif" placeholder="Expliquez la raison de votre demande..."></textarea>
                </div>
                <div id="adresseGroup" class="form-group" style="display: none;">
                    <label>Adresse de livraison *</label>
                    <textarea id="demandeAdresse" placeholder="Votre adresse complète..."></textarea>
                </div>
                <button class="btn-primary" onclick="soumettreDemande('${archive.id}')">Soumettre la demande</button>
            </div>
        `;
        
        // Gestion de l'affichage de l'adresse
        document.getElementById('demandeType').addEventListener('change', (e) => {
            const adresseGroup = document.getElementById('adresseGroup');
            adresseGroup.style.display = e.target.value === 'envoi' ? 'block' : 'none';
        });
        
        // Sélection des tarifs
        document.querySelectorAll('.tarif-card').forEach(card => {
            card.addEventListener('click', () => {
                document.querySelectorAll('.tarif-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                document.getElementById('demandeType').value = card.dataset.type;
                const adresseGroup = document.getElementById('adresseGroup');
                adresseGroup.style.display = card.dataset.type === 'envoi' ? 'block' : 'none';
            });
        });
        
    } catch (error) {
        console.error('Erreur:', error);
        modalBody.innerHTML = '<div class="error-state">Erreur de chargement</div>';
    }
}

// Soumettre une demande d'accès
async function soumettreDemande(archiveId) {
    const type = document.getElementById('demandeType').value;
    const motif = document.getElementById('demandeMotif').value;
    const adresse = document.getElementById('demandeAdresse')?.value || '';
    
    if (!motif) {
        alert('Veuillez indiquer le motif de votre demande');
        return;
    }
    
    if (type === 'envoi' && !adresse) {
        alert('Veuillez indiquer votre adresse de livraison');
        return;
    }
    
    const token = localStorage.getItem('access_token');
    if (!token) {
        alert('Veuillez vous connecter pour effectuer une demande');
        window.location.href = 'login.html';
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/archives/${archiveId}/demander_acces/`, {
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
            alert('Demande envoyée avec succès ! Vous recevrez une notification sous 48h.');
            closeModal();
            if (document.querySelector('.tab-btn[data-tab="mes-demandes"]')) {
                document.querySelector('.tab-btn[data-tab="mes-demandes"]').click();
            }
        } else {
            const error = await response.json();
            alert('Erreur: ' + (error.error || 'Impossible d\'envoyer la demande'));
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur de connexion');
    }
}

// Charger mes demandes
async function loadMesDemandes() {
    const container = document.getElementById('demandesList');
    container.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';
    
    try {
        const token = localStorage.getItem('access_token');
        if (!token) {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-lock"></i><p>Connectez-vous pour voir vos demandes</p><a href="login.html" class="btn-primary">Se connecter</a></div>';
            return;
        }
        
        const response = await fetch(`${API_URL}/demandes/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const demandes = await response.json();
        
        if (demandes.length > 0) {
            renderDemandes(demandes);
        } else {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>Aucune demande effectuée</p></div>';
        }
    } catch (error) {
        console.error('Erreur:', error);
        container.innerHTML = '<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Erreur de chargement</p></div>';
    }
}

// Afficher les demandes
function renderDemandes(demandes) {
    const container = document.getElementById('demandesList');
    container.innerHTML = '';
    
    demandes.forEach(demande => {
        const item = document.createElement('div');
        item.className = 'demande-item';
        item.style.borderLeftColor = getStatutCouleur(demande.statut);
        
        item.innerHTML = `
            <div class="demande-statut statut-${demande.statut}">${getStatutTexte(demande.statut)}</div>
            <div class="archive-reference">${demande.archive_reference}</div>
            <div class="archive-titre">${demande.archive_titre}</div>
            <div class="detail-row">
                <div class="detail-label">Type :</div>
                <div class="detail-value">${getTypeTexte(demande.type_demande)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Date :</div>
                <div class="detail-value">${new Date(demande.date_demande).toLocaleDateString('fr-FR')}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">Montant :</div>
                <div class="detail-value">${demande.montant_calcule} FCFA</div>
            </div>
            ${demande.statut === 'valide' ? `
                <button class="btn-primary" style="margin-top: 12px;" onclick="effectuerPaiement('${demande.id}', ${demande.montant_calcule})">Payer ${demande.montant_calcule} FCFA</button>
            ` : ''}
            ${demande.statut === 'paye' ? `
                <button class="btn-primary" style="margin-top: 12px;" onclick="telechargerDocument('${demande.id}')"><i class="fas fa-download"></i> Télécharger</button>
            ` : ''}
            ${demande.commentaire_moderation ? `
                <div class="detail-row" style="margin-top: 12px;">
                    <div class="detail-label">Commentaire :</div>
                    <div class="detail-value">${demande.commentaire_moderation}</div>
                </div>
            ` : ''}
        `;
        container.appendChild(item);
    });
}

// Effectuer le paiement
async function effectuerPaiement(demandeId, montant) {
    if (confirm(`Confirmer le paiement de ${montant} FCFA ?`)) {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`${API_URL}/demandes/${demandeId}/effectuer_paiement/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                alert('Paiement effectué avec succès ! Le document est maintenant disponible au téléchargement.');
                loadMesDemandes();
            } else {
                alert('Erreur lors du paiement');
            }
        } catch (error) {
            console.error('Erreur:', error);
            alert('Erreur de connexion');
        }
    }
}

// Télécharger le document
async function telechargerDocument(demandeId) {
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_URL}/demandes/${demandeId}/telecharger/`, {
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
        } else {
            alert('Erreur lors du téléchargement');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur de connexion');
    }
}

// Pagination
function renderPagination(total) {
    const pages = Math.ceil(total / 10);
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';
    
    for (let i = 1; i <= Math.min(pages, 10); i++) {
        const btn = document.createElement('button');
        btn.textContent = i;
        btn.className = i === currentPage ? 'active' : '';
        btn.onclick = () => {
            currentPage = i;
            loadArchives();
        };
        pagination.appendChild(btn);
    }
}

// Utilitaires
function getStatutCouleur(statut) {
    const couleurs = {
        'en_attente': '#f59e0b',
        'valide': '#10b981',
        'paye': '#4f46e5',
        'rejetee': '#ef4444',
        'livree': '#10b981'
    };
    return couleurs[statut] || '#6b7280';
}

function getStatutTexte(statut) {
    const textes = {
        'en_attente': 'En attente de validation',
        'valide': 'Validée - En attente de paiement',
        'paye': 'Payée - Disponible',
        'rejetee': 'Rejetée',
        'livree': 'Livrée'
    };
    return textes[statut] || statut;
}

function getTypeTexte(type) {
    const textes = {
        'consultation': 'Consultation sur place',
        'copie': 'Copie numérique',
        'impression': 'Impression papier',
        'envoi': 'Envoi par courrier'
    };
    return textes[type] || type;
}

function closeModal() {
    document.getElementById('archiveModal').classList.remove('active');
}

function closeDemandeModal() {
    document.getElementById('demandeModal').classList.remove('active');
}