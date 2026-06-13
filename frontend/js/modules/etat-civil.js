/**
 * MODULE ÉTAT CIVIL
 * Gestion des actes d'état civil
 */

// Configuration
const API_URL = 'http://localhost:8000/api';
let currentStep = 1;
const totalSteps = 6;

// Données géographiques Cameroun
const regions = [
    { id: 1, nom: 'Adamaoua' },
    { id: 2, nom: 'Centre' },
    { id: 3, nom: 'Est' },
    { id: 4, nom: 'Extrême-Nord' },
    { id: 5, nom: 'Littoral' },
    { id: 6, nom: 'Nord' },
    { id: 7, nom: 'Nord-Ouest' },
    { id: 8, nom: 'Ouest' },
    { id: 9, nom: 'Sud' },
    { id: 10, nom: 'Sud-Ouest' }
];

// Départements par région
const departements = {
    2: [ // Centre
        { id: 1, nom: 'Haute-Sanaga' },
        { id: 2, nom: 'Lekié' },
        { id: 3, nom: 'Mbam-et-Inoubou' },
        { id: 4, nom: 'Mbam-et-Kim' },
        { id: 5, nom: 'Méfou-et-Afamba' },
        { id: 6, nom: 'Méfou-et-Akono' },
        { id: 7, nom: 'Mfoundi' },
        { id: 8, nom: 'Nyong-et-Kellé' },
        { id: 9, nom: 'Nyong-et-Mfoumou' },
        { id: 10, nom: 'Nyong-et-So\'o' }
    ],
    5: [ // Littoral
        { id: 11, nom: 'Moungo' },
        { id: 12, nom: 'Nkam' },
        { id: 13, nom: 'Sanaga-Maritime' },
        { id: 14, nom: 'Wouri' }
    ]
};

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    initRegions();
    initFormNavigation();
    initDateTarif();
    
    // Charger les demandes
    loadMesDemandes();
});

// Initialiser les régions
function initRegions() {
    const regionSelect = document.getElementById('region');
    if (regionSelect) {
        regions.forEach(region => {
            const option = document.createElement('option');
            option.value = region.id;
            option.textContent = region.nom;
            regionSelect.appendChild(option);
        });
        
        regionSelect.addEventListener('change', () => {
            const departementSelect = document.getElementById('departement');
            const regionId = parseInt(regionSelect.value);
            
            departementSelect.innerHTML = '<option value="">Sélectionnez un département</option>';
            departementSelect.disabled = !regionId;
            
            if (regionId && departements[regionId]) {
                departements[regionId].forEach(dept => {
                    const option = document.createElement('option');
                    option.value = dept.id;
                    option.textContent = dept.nom;
                    departementSelect.appendChild(option);
                });
            }
        });
    }
}

// Navigation du formulaire
function initFormNavigation() {
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const submitBtn = document.getElementById('submitBtn');
    const form = document.getElementById('naissanceForm');
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (validateStep(currentStep)) {
                showStep(currentStep + 1);
            }
        });
    }
    
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            showStep(currentStep - 1);
        });
    }
    
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            submitDemande();
        });
    }
}

// Afficher une étape
function showStep(step) {
    if (step < 1 || step > totalSteps) return;
    
    // Cacher toutes les étapes
    for (let i = 1; i <= totalSteps; i++) {
        const stepDiv = document.getElementById(`step${i}`);
        if (stepDiv) stepDiv.classList.remove('active');
        const stepIndicator = document.querySelector(`.step[data-step="${i}"]`);
        if (stepIndicator) stepIndicator.classList.remove('active');
    }
    
    // Afficher l'étape courante
    const currentStepDiv = document.getElementById(`step${step}`);
    if (currentStepDiv) currentStepDiv.classList.add('active');
    const currentStepIndicator = document.querySelector(`.step[data-step="${step}"]`);
    if (currentStepIndicator) currentStepIndicator.classList.add('active');
    
    currentStep = step;
    
    // Gérer les boutons
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const submitBtn = document.getElementById('submitBtn');
    
    if (prevBtn) prevBtn.style.display = step === 1 ? 'none' : 'flex';
    if (nextBtn) nextBtn.style.display = step === totalSteps ? 'none' : 'flex';
    if (submitBtn) submitBtn.style.display = step === totalSteps ? 'flex' : 'none';
    
    // Mettre à jour le récapitulatif si dernière étape
    if (step === totalSteps) {
        updateRecapitulatif();
    }
}

// Valider une étape
function validateStep(step) {
    let isValid = true;
    
    switch(step) {
        case 1:
            isValid = validateGeographique();
            break;
        case 2:
            isValid = validateEnfant();
            break;
        case 3:
            isValid = validateMere();
            break;
        case 4:
            isValid = validatePere();
            break;
        case 5:
            isValid = validateDeclarant();
            break;
    }
    
    if (!isValid) {
        showNotification('Veuillez remplir tous les champs obligatoires', 'error');
    }
    
    return isValid;
}

// Validation des sections
function validateGeographique() {
    const region = document.getElementById('region').value;
    const departement = document.getElementById('departement').value;
    const arrondissement = document.getElementById('arrondissement').value;
    const lieuNaissance = document.getElementById('lieuNaissance').value;
    
    return region && departement && arrondissement && lieuNaissance;
}

function validateEnfant() {
    const nom = document.getElementById('enfantNom').value;
    const prenom = document.getElementById('enfantPrenom').value;
    const dateNaissance = document.getElementById('enfantDateNaissance').value;
    const sexe = document.getElementById('enfantSexe').value;
    
    return nom && prenom && dateNaissance && sexe;
}

function validateMere() {
    const nom = document.getElementById('mereNom').value;
    const prenom = document.getElementById('merePrenom').value;
    const dateNaissance = document.getElementById('mereDateNaissance').value;
    
    return nom && prenom && dateNaissance;
}

function validatePere() {
    const nom = document.getElementById('pereNom').value;
    const prenom = document.getElementById('perePrenom').value;
    
    return nom && prenom;
}

function validateDeclarant() {
    const nom = document.getElementById('declarantNom').value;
    const prenom = document.getElementById('declarantPrenom').value;
    const qualite = document.getElementById('declarantQualite').value;
    const attestation = document.getElementById('declarantAttestation').checked;
    
    return nom && prenom && qualite && attestation;
}

// Calcul du tarif
function initDateTarif() {
    const dateInput = document.getElementById('enfantDateNaissance');
    if (dateInput) {
        dateInput.addEventListener('change', calculerTarif);
    }
}

function calculerTarif() {
    const dateNaissance = new Date(document.getElementById('enfantDateNaissance').value);
    if (!dateNaissance) return;
    
    const aujourdhui = new Date();
    const diffJours = Math.floor((aujourdhui - dateNaissance) / (1000 * 60 * 60 * 24));
    
    let tarif;
    if (diffJours <= 45) {
        tarif = 1000; // Tarif normal
    } else {
        tarif = 10000; // Tarif majoré
    }
    
    const tarifSpan = document.getElementById('tarifEstime');
    if (tarifSpan) tarifSpan.textContent = tarif;
}

// Mettre à jour le récapitulatif
function updateRecapitulatif() {
    const recapDiv = document.getElementById('recapitulatif');
    if (!recapDiv) return;
    
    const enfantNom = document.getElementById('enfantNom').value;
    const enfantPrenom = document.getElementById('enfantPrenom').value;
    const mereNom = document.getElementById('mereNom').value;
    const merePrenom = document.getElementById('merePrenom').value;
    const pereNom = document.getElementById('pereNom').value;
    const perePrenom = document.getElementById('perePrenom').value;
    
    recapDiv.innerHTML = `
        <div class="recap-section">
            <h4>Enfant</h4>
            <p><strong>Nom:</strong> ${enfantNom} ${enfantPrenom}</p>
            <p><strong>Date de naissance:</strong> ${document.getElementById('enfantDateNaissance').value}</p>
        </div>
        <div class="recap-section">
            <h4>Mère</h4>
            <p><strong>Nom:</strong> ${mereNom} ${merePrenom}</p>
            <p><strong>Téléphone:</strong> ${document.getElementById('mereTelephone1').value}</p>
        </div>
        <div class="recap-section">
            <h4>Père</h4>
            <p><strong>Nom:</strong> ${pereNom} ${perePrenom}</p>
        </div>
    `;
}

// Soumettre la demande
async function submitDemande() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        showNotification('Veuillez vous connecter', 'error');
        setTimeout(() => {
            window.location.href = '../accounts/login.html';
        }, 2000);
        return;
    }
    
    const formData = {
        // Géographique
        region: document.getElementById('region').value,
        departement: document.getElementById('departement').value,
        arrondissement: document.getElementById('arrondissement').value,
        lieu_naissance: document.getElementById('lieuNaissance').value,
        
        // Enfant
        enfant_nom: document.getElementById('enfantNom').value,
        enfant_prenom: document.getElementById('enfantPrenom').value,
        enfant_date_naissance: document.getElementById('enfantDateNaissance').value,
        enfant_sexe: document.getElementById('enfantSexe').value,
        enfant_poids: document.getElementById('enfantPoids').value,
        enfant_taille: document.getElementById('enfantTaille').value,
        
        // Mère
        mere_nom: document.getElementById('mereNom').value,
        mere_prenom: document.getElementById('merePrenom').value,
        mere_date_naissance: document.getElementById('mereDateNaissance').value,
        mere_telephone1: document.getElementById('mereTelephone1').value,
        mere_telephone2: document.getElementById('mereTelephone2').value,
        mere_situation_matrimoniale: document.getElementById('mereSituationMatrimoniale').value,
        mere_nationalite: document.getElementById('mereNationalite').value,
        
        // Père
        pere_nom: document.getElementById('pereNom').value,
        pere_prenom: document.getElementById('perePrenom').value,
        pere_telephone1: document.getElementById('pereTelephone1').value,
        
        // Déclarant
        declarant_nom: document.getElementById('declarantNom').value,
        declarant_prenom: document.getElementById('declarantPrenom').value,
        declarant_qualite: document.getElementById('declarantQualite').value,
        declarant_telephone: document.getElementById('declarantTelephone').value
    };
    
    showNotification('Envoi de la demande...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/etat-civil/naissance/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            showNotification('Demande envoyée avec succès !', 'success');
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);
        } else {
            const error = await response.json();
            showNotification(error.error || 'Erreur lors de l\'envoi', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('Erreur de connexion', 'error');
    }
}

// Charger mes demandes
async function loadMesDemandes() {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    try {
        const response = await fetch(`${API_URL}/etat-civil/demandes/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const demandes = await response.json();
        
        displayDemandes(demandes);
    } catch (error) {
        console.error('Erreur:', error);
    }
}

// Afficher les demandes
function displayDemandes(demandes) {
    const encoursContainer = document.getElementById('demandesEnCours');
    const traiteesContainer = document.getElementById('demandesTraitees');
    
    if (!encoursContainer || !traiteesContainer) return;
    
    const encours = demandes.filter(d => ['en_attente', 'en_cours', 'valide'].includes(d.statut));
    const traitees = demandes.filter(d => ['rejete', 'delivre'].includes(d.statut));
    
    encoursContainer.innerHTML = encours.length ? renderDemandesList(encours) : '<div class="empty-state"><i class="fas fa-inbox"></i><p>Aucune demande en cours</p></div>';
    traiteesContainer.innerHTML = traitees.length ? renderDemandesList(traitees) : '<div class="empty-state"><i class="fas fa-check-circle"></i><p>Aucune demande traitée</p></div>';
}

function renderDemandesList(demandes) {
    return demandes.map(demande => `
        <div class="demande-item" style="border-left-color: ${getStatutCouleur(demande.statut)}">
            <div class="demande-statut ${getStatutClass(demande.statut)}">
                <i class="fas ${getStatutIcon(demande.statut)}"></i> ${getStatutTexte(demande.statut)}
            </div>
            <div class="archive-reference">${demande.reference || 'N/A'}</div>
            <div class="archive-titre">${demande.type_acte === 'naissance' ? 'Acte de naissance' : demande.type_acte}</div>
            <div class="demande-details">
                <span><i class="fas fa-calendar"></i> ${new Date(demande.date_creation).toLocaleDateString('fr-FR')}</span>
            </div>
            <div class="demande-actions">
                <button class="btn-download" onclick="voirSuivi('${demande.id}')"><i class="fas fa-chart-line"></i> Suivre</button>
            </div>
        </div>
    `).join('');
}

function getStatutCouleur(statut) {
    const couleurs = {
        'en_attente': '#f59e0b',
        'en_cours': '#3b82f6',
        'valide': '#10b981',
        'rejete': '#ef4444',
        'delivre': '#10b981'
    };
    return couleurs[statut] || '#6c757d';
}

function getStatutClass(statut) {
    return `statut-${statut}`;
}

function getStatutIcon(statut) {
    const icons = {
        'en_attente': 'fa-clock',
        'en_cours': 'fa-spinner fa-pulse',
        'valide': 'fa-check-circle',
        'rejete': 'fa-times-circle',
        'delivre': 'fa-file-pdf'
    };
    return icons[statut] || 'fa-question';
}

function getStatutTexte(statut) {
    const textes = {
        'en_attente': 'En attente de validation',
        'en_cours': 'En cours de traitement',
        'valide': 'Validé - En attente signature',
        'rejete': 'Rejeté',
        'delivre': 'Délivré'
    };
    return textes[statut] || statut;
}

// Voir suivi
function voirSuivi(demandeId) {
    window.location.href = `suivi.html?id=${demandeId}`;
}

// Tabs
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`${btn.dataset.tab}Tab`).classList.add('active');
    });
});

// Notification
function showNotification(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i> ${message}`;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#667eea'};
        color: white;
        border-radius: 12px;
        z-index: 9999;
        animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}