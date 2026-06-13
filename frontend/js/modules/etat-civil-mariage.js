/**
 * MODULE ÉTAT CIVIL - ACTE DE MARIAGE
 */

let currentStep = 1;
const totalSteps = 5;
let temoinsCount = 2;

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initTemoins();
});

function initNavigation() {
    document.getElementById('prevBtn').onclick = () => showStep(currentStep - 1);
    document.getElementById('nextBtn').onclick = () => showStep(currentStep + 1);
    document.getElementById('submitBtn').onclick = (e) => { e.preventDefault(); submitForm(); };
}

function showStep(step) {
    if (step < 1 || step > totalSteps) return;
    if (step > currentStep && !validateStep(currentStep)) return;
    
    for (let i = 1; i <= totalSteps; i++) {
        document.getElementById(`step${i}`).classList.remove('active');
        document.querySelector(`.step[data-step="${i}"]`).classList.remove('active');
    }
    
    document.getElementById(`step${step}`).classList.add('active');
    document.querySelector(`.step[data-step="${step}"]`).classList.add('active');
    
    document.getElementById('prevBtn').style.display = step === 1 ? 'none' : 'inline-flex';
    document.getElementById('nextBtn').style.display = step === totalSteps ? 'none' : 'inline-flex';
    document.getElementById('submitBtn').style.display = step === totalSteps ? 'inline-flex' : 'none';
    
    if (step === totalSteps) updateRecap();
    
    currentStep = step;
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function validateStep(step) {
    switch(step) {
        case 1:
            return validateRequired(['epouxNom', 'epouxPrenom', 'epouxDateNaissance', 'epouxLieuNaissance']);
        case 2:
            return validateRequired(['epouseNom', 'epousePrenom', 'epouseDateNaissance', 'epouseLieuNaissance']);
        case 3:
            return validateTemoins();
        case 4:
            return validateRequired(['dateMariage', 'lieuMariage']) && 
                   document.getElementById('consentementEpoux').checked && 
                   document.getElementById('consentementEpouse').checked;
        default:
            return true;
    }
}

function validateRequired(fields) {
    let valid = true;
    fields.forEach(id => {
        const el = document.getElementById(id);
        if (!el.value) {
            el.classList.add('error');
            valid = false;
        } else {
            el.classList.remove('error');
        }
    });
    return valid;
}

function validateTemoins() {
    const nomInputs = document.querySelectorAll('.temoins-nom');
    const prenomInputs = document.querySelectorAll('.temoins-prenom');
    let valid = true;
    
    for (let i = 0; i < nomInputs.length; i++) {
        if (!nomInputs[i].value) {
            nomInputs[i].classList.add('error');
            valid = false;
        } else {
            nomInputs[i].classList.remove('error');
        }
        if (!prenomInputs[i].value) {
            prenomInputs[i].classList.add('error');
            valid = false;
        } else {
            prenomInputs[i].classList.remove('error');
        }
    }
    return valid && nomInputs.length >= 2;
}

function initTemoins() {
    document.getElementById('addTemoinBtn').onclick = () => {
        if (temoinsCount >= 4) {
            showNotification('Maximum 4 témoins', 'warning');
            return;
        }
        temoinsCount++;
        const container = document.getElementById('temoins-container');
        const newTemoin = document.createElement('div');
        newTemoin.className = 'temoins-group';
        newTemoin.setAttribute('data-index', temoinsCount - 1);
        newTemoin.innerHTML = `
            <h4>Témoin ${temoinsCount} <button type="button" class="btn-remove" onclick="removeTemoin(this)"><i class="fas fa-trash"></i></button></h4>
            <div class="form-row">
                <div class="form-group"><label>Nom *</label><input type="text" class="temoins-nom" required></div>
                <div class="form-group"><label>Prénom *</label><input type="text" class="temoins-prenom" required></div>
            </div>
        `;
        container.appendChild(newTemoin);
    };
}

function removeTemoin(btn) {
    const group = btn.closest('.temoins-group');
    if (document.querySelectorAll('.temoins-group').length > 2) {
        group.remove();
        temoinsCount--;
        // Re-indexer
        document.querySelectorAll('.temoins-group').forEach((g, idx) => {
            g.setAttribute('data-index', idx);
            g.querySelector('h4').innerHTML = `Témoin ${idx + 1} <button type="button" class="btn-remove" onclick="removeTemoin(this)"><i class="fas fa-trash"></i></button>`;
        });
    } else {
        showNotification('Minimum 2 témoins requis', 'warning');
    }
}

function updateRecap() {
    document.getElementById('recapitulatif').innerHTML = `
        <div class="recap-section">
            <h4>👨 Époux</h4>
            <p><strong>Nom:</strong> ${document.getElementById('epouxNom').value} ${document.getElementById('epouxPrenom').value}</p>
            <p><strong>Né le:</strong> ${document.getElementById('epouxDateNaissance').value}</p>
            <p><strong>Tél:</strong> ${document.getElementById('epouxTelephone').value || 'Non renseigné'}</p>
        </div>
        <div class="recap-section">
            <h4>👩 Épouse</h4>
            <p><strong>Nom:</strong> ${document.getElementById('epouseNom').value} ${document.getElementById('epousePrenom').value}</p>
            <p><strong>Née le:</strong> ${document.getElementById('epouseDateNaissance').value}</p>
            <p><strong>Tél:</strong> ${document.getElementById('epouseTelephone').value || 'Non renseigné'}</p>
        </div>
        <div class="recap-section">
            <h4>💒 Mariage</h4>
            <p><strong>Date:</strong> ${document.getElementById('dateMariage').value}</p>
            <p><strong>Lieu:</strong> ${document.getElementById('lieuMariage').value}</p>
            <p><strong>Régime:</strong> ${document.getElementById('regimeMatrimonial').options[document.getElementById('regimeMatrimonial').selectedIndex]?.text}</p>
        </div>
    `;
}

async function submitForm() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        showNotification('Veuillez vous connecter', 'error');
        setTimeout(() => window.location.href = '../accounts/login.html', 2000);
        return;
    }
    
    const temoins = [];
    document.querySelectorAll('.temoins-group').forEach(group => {
        temoins.push({
            nom: group.querySelector('.temoins-nom').value,
            prenom: group.querySelector('.temoins-prenom').value
        });
    });
    
    const data = {
        epoux_nom: document.getElementById('epouxNom').value,
        epoux_prenom: document.getElementById('epouxPrenom').value,
        epoux_date_naissance: document.getElementById('epouxDateNaissance').value,
        epoux_lieu_naissance: document.getElementById('epouxLieuNaissance').value,
        epoux_domicile: document.getElementById('epouxDomicile').value,
        epoux_profession: document.getElementById('epouxProfession').value,
        epoux_telephone: document.getElementById('epouxTelephone').value,
        epouse_nom: document.getElementById('epouseNom').value,
        epouse_prenom: document.getElementById('epousePrenom').value,
        epouse_date_naissance: document.getElementById('epouseDateNaissance').value,
        epouse_lieu_naissance: document.getElementById('epouseLieuNaissance').value,
        epouse_domicile: document.getElementById('epouseDomicile').value,
        epouse_profession: document.getElementById('epouseProfession').value,
        epouse_telephone: document.getElementById('epouseTelephone').value,
        date_mariage: document.getElementById('dateMariage').value,
        lieu_mariage: document.getElementById('lieuMariage').value,
        regime_matrimonial: document.getElementById('regimeMatrimonial').value,
        temoins: temoins,
        consentement_epoux: document.getElementById('consentementEpoux').checked,
        consentement_epouse: document.getElementById('consentementEpouse').checked
    };
    
    showNotification('Envoi en cours...', 'info');
    
    try {
        const response = await fetch('http://localhost:8000/api/etat-civil/demandes/mariage/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            showNotification('Demande envoyée avec succès !', 'success');
            setTimeout(() => window.location.href = 'index.html', 2000);
        } else {
            const error = await response.json();
            showNotification(error.error || 'Erreur lors de l\'envoi', 'error');
        }
    } catch (error) {
        showNotification('Erreur de connexion', 'error');
    }
}

function showNotification(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i> ${message}`;
    toast.style.cssText = `
        position: fixed; bottom: 20px; right: 20px; padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#667eea'};
        color: white; border-radius: 12px; z-index: 9999; animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

window.removeTemoin = removeTemoin;