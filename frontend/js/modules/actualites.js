// frontend/js/modules/actualites.js

// Configuration de l'API
const API_BASE = 'http://localhost:8000/api/actualites';

// État global
let currentPage = 1;
let currentFilters = {
    categorie: '',
    search: '',
    ordering: '-date_publication'
};

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    initActualites();
});

function initActualites() {
    loadCategories();
    loadPublications();
    setupEventListeners();
}

// Chargement des catégories
async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE}/categories/`);
        const categories = await response.json();
        
        const selectCategorie = document.getElementById('categorie-filter');
        if (selectCategorie) {
            selectCategorie.innerHTML = '<option value="">Toutes les catégories</option>';
            categories.forEach(cat => {
                selectCategorie.innerHTML += `<option value="${cat.slug}">${cat.nom}</option>`;
            });
        }
    } catch (error) {
        console.error('Erreur chargement catégories:', error);
    }
}

// Chargement des publications
async function loadPublications() {
    const grid = document.getElementById('actualites-grid');
    if (!grid) return;
    
    // Afficher le loader
    grid.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        // Construire l'URL avec les filtres
        let url = `${API_BASE}/publications/?page=${currentPage}&ordering=${currentFilters.ordering}`;
        if (currentFilters.categorie) url += `&categorie=${currentFilters.categorie}`;
        if (currentFilters.search) url += `&search=${encodeURIComponent(currentFilters.search)}`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            renderPublications(data.results);
            renderPagination(data);
        } else {
            grid.innerHTML = '<div class="no-results">Aucune actualité trouvée</div>';
        }
    } catch (error) {
        console.error('Erreur chargement publications:', error);
        grid.innerHTML = '<div class="error-message">Erreur de chargement des actualités</div>';
    }
}

// Rendu des publications
function renderPublications(publications) {
    const grid = document.getElementById('actualites-grid');
    if (!grid) return;
    
    grid.innerHTML = publications.map(pub => `
        <article class="news-card ${pub.est_epingle ? 'epingle' : ''}" data-id="${pub.id}">
            ${renderBadges(pub)}
            ${renderMedia(pub)}
            <div class="news-content">
                <span class="news-category" style="background: ${pub.categorie_couleur}20; color: ${pub.categorie_couleur}">
                    ${pub.categorie_nom}
                </span>
                <h3 class="news-title">
                    <a href="detail.html?id=${pub.id}">${escapeHtml(pub.titre)}</a>
                </h3>
                <p class="news-excerpt">${escapeHtml(pub.accroche)}</p>
                <div class="news-meta">
                    <span><i class="fas fa-user"></i> ${pub.auteur_nom}</span>
                    <span><i class="fas fa-calendar"></i> ${formatDate(pub.date_publication)}</span>
                    <div class="news-stats">
                        <span><i class="fas fa-eye"></i> ${pub.vue_count}</span>
                        <span><i class="fas fa-heart"></i> ${pub.reactions_count || 0}</span>
                        <span><i class="fas fa-comment"></i> ${pub.commentaires_count || 0}</span>
                    </div>
                </div>
            </div>
        </article>
    `).join('');
}

// Rendu des badges
function renderBadges(pub) {
    let badges = '';
    if (pub.est_epingle) {
        badges += '<div class="badge-epingle"><i class="fas fa-thumbtack"></i> Épinglé</div>';
    }
    if (pub.est_a_la_une) {
        badges += '<div class="badge-a-la-une"><i class="fas fa-star"></i> À la une</div>';
    }
    return badges ? `<div class="news-badge">${badges}</div>` : '';
}

// Rendu du média
function renderMedia(pub) {
    if (pub.type_media === 'video' && pub.media_url) {
        return `
            <div class="news-media">
                <video src="${pub.media_url}" poster="${pub.thumbnail || ''}"></video>
                <div class="media-icon"><i class="fas fa-play"></i></div>
            </div>
        `;
    } else if (pub.media) {
        return `
            <div class="news-media">
                <img src="${pub.media}" alt="${escapeHtml(pub.titre)}" loading="lazy">
                <div class="media-icon"><i class="fas fa-image"></i></div>
            </div>
        `;
    }
    return `
        <div class="news-media" style="background: linear-gradient(135deg, #667eea, #764ba2)">
            <div class="media-icon"><i class="fas fa-newspaper"></i></div>
        </div>
    `;
}

// Pagination
function renderPagination(data) {
    const pagination = document.getElementById('pagination');
    if (!pagination) return;
    
    if (data.total_pages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = '<div class="pagination-container"><div class="pagination">';
    
    // Previous
    if (data.has_previous) {
        html += `<button class="page-btn" data-page="${data.previous_page_number}"><i class="fas fa-chevron-left"></i></button>`;
    }
    
    // Pages
    for (let i = 1; i <= data.total_pages; i++) {
        if (i === currentPage) {
            html += `<button class="page-btn active" data-page="${i}">${i}</button>`;
        } else if (Math.abs(i - currentPage) <= 2) {
            html += `<button class="page-btn" data-page="${i}">${i}</button>`;
        } else if (Math.abs(i - currentPage) === 3) {
            html += '<span>...</span>';
        }
    }
    
    // Next
    if (data.has_next) {
        html += `<button class="page-btn" data-page="${data.next_page_number}"><i class="fas fa-chevron-right"></i></button>`;
    }
    
    html += '</div></div>';
    pagination.innerHTML = html;
    
    // Attacher events
    document.querySelectorAll('.page-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentPage = parseInt(btn.dataset.page);
            loadPublications();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });
}

// Configuration des événements
function setupEventListeners() {
    // Filtre catégorie
    const categorieFilter = document.getElementById('categorie-filter');
    if (categorieFilter) {
        categorieFilter.addEventListener('change', (e) => {
            currentFilters.categorie = e.target.value;
            currentPage = 1;
            loadPublications();
        });
    }
    
    // Recherche
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    
    function performSearch() {
        currentFilters.search = searchInput.value;
        currentPage = 1;
        loadPublications();
    }
    
    if (searchBtn) searchBtn.addEventListener('click', performSearch);
    if (searchInput) searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });
    
    // Tri
    const orderSelect = document.getElementById('order-select');
    if (orderSelect) {
        orderSelect.addEventListener('change', (e) => {
            currentFilters.ordering = e.target.value;
            currentPage = 1;
            loadPublications();
        });
    }
}

// Page détail
async function loadPublicationDetail() {
    const urlParams = new URLSearchParams(window.location.search);
    const publicationId = urlParams.get('id');
    
    if (!publicationId) return;
    
    const container = document.getElementById('detail-container');
    if (!container) return;
    
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        // Incrémenter la vue
        await fetch(`${API_BASE}/publications/${publicationId}/increment_vue/`, { method: 'POST' });
        
        // Charger les détails
        const response = await fetch(`${API_BASE}/publications/${publicationId}/`);
        const pub = await response.json();
        
        renderPublicationDetail(pub);
        loadCommentaires(publicationId);
        loadReactions(publicationId);
        
    } catch (error) {
        console.error('Erreur:', error);
        container.innerHTML = '<div class="error-message">Impossible de charger l\'article</div>';
    }
}

function renderPublicationDetail(pub) {
    const container = document.getElementById('detail-container');
    container.innerHTML = `
        <article class="detail-container">
            <div class="detail-header">
                <span class="news-category" style="background: ${pub.categorie.couleur}20; color: ${pub.categorie.couleur}">
                    ${pub.categorie.nom}
                </span>
                <h1 class="detail-title">${escapeHtml(pub.titre)}</h1>
                <div class="detail-meta">
                    <div>
                        <i class="fas fa-user"></i> ${pub.auteur_nom} | 
                        <i class="fas fa-calendar"></i> ${formatDate(pub.date_publication)} |
                        <i class="fas fa-clock"></i> ${pub.temps_lecture} min de lecture
                    </div>
                    <div class="detail-stats">
                        <span><i class="fas fa-eye"></i> ${pub.vue_count} vues</span>
                        <span><i class="fas fa-share-alt"></i> ${pub.partage_count} partages</span>
                    </div>
                </div>
            </div>
            
            ${renderDetailMedia(pub)}
            
            <div class="detail-content">
                ${pub.contenu}
            </div>
            
            <div class="reactions-section">
                <h3>Réagissez à cet article</h3>
                <div class="reactions-buttons" id="reactions-buttons">
                    ${renderReactionButtons(pub.reaction_utilisateur)}
                </div>
                <div class="reactions-summary" id="reactions-summary">
                    ${renderReactionsSummary(pub.reactions)}
                </div>
            </div>
            
            <div class="share-section">
                <button class="share-btn" data-platform="facebook"><i class="fab fa-facebook"></i> Partager</button>
                <button class="share-btn" data-platform="twitter"><i class="fab fa-twitter"></i> Tweeter</button>
                <button class="share-btn" data-platform="whatsapp"><i class="fab fa-whatsapp"></i> WhatsApp</button>
                <button class="share-btn" data-platform="linkedin"><i class="fab fa-linkedin"></i> LinkedIn</button>
            </div>
            
            <div class="commentaires-section" id="commentaires-section">
                <h3>Commentaires (${pub.commentaires?.length || 0})</h3>
                <div class="comment-form">
                    <textarea id="comment-content" class="comment-input" rows="3" placeholder="Partagez votre avis..."></textarea>
                    <button id="submit-comment" class="btn-primary">Publier le commentaire</button>
                </div>
                <div id="commentaires-list"></div>
            </div>
        </article>
    `;
    
    // Attacher les événements
    attachReactionEvents(pub.id);
    attachShareEvents(pub.id);
    attachCommentEvent(pub.id);
}

// Utilitaires
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i> ${message}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Exporter les fonctions pour usage global
window.actualitesModule = {
    loadPublications,
    loadPublicationDetail,
    showToast
};