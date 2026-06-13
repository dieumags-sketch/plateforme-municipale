/**
 * MODULE ÉTAT CIVIL - ACTE DE DÉCÈS
 */

let currentStep = 1;
const totalSteps = 4;

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
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
            return validateRequired(['defuntNom', 'defuntPrenom', 'defuntDateNaissance', 'defuntLieuNaissance']);
        case 2:
            return validateRequired(['dateDeces', 'lieuDeces']);
        case 3:
            return validateRequired(['declarantNom', 'declarantPrenom', 'declarantQualite']);
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

function updateRecap() {
    document.getElementById('recapitulatif').innerHTML = `
        <div class="recap-section">
            <h4>🕊️ Défunt</h4>
            <p><strong>Nom:</strong> ${document.getElementById('defuntNom').value} ${document.getElementById('defuntPrenom').value}</p>
            <p><strong>Né le:</strong> ${document.getElementById('defuntDateNaissance').value}</p>
            <p><strong>Profession:</strong> ${document.getElementById('defuntProfession').value || 'Non renseigné'}</p>
        </div>
        <div class="recap-section">
            <h4>📅 Décès</h4>
            <p><strong>Date:</strong> ${document.getElementById('dateDeces').value}</p>
            <p><strong>Lieu:</strong> ${document.getElementById('lieuDeces').value}</p>
            <p><strong>Cause:</strong> ${document.getElementById('causeDeces').value || 'Non précisée'}</p>
        </div>
        <div class="recap-section">
            <h4>👤 Déclarant</h4>
            <p><strong>Nom:</strong> ${document.getElementById('declarantNom').value} ${document.getElementById('declarantPrenom').value}</p>
            <p><strong>Qualité:</strong> ${document.getElementById('declarantQualite').value}</p>
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
    
    const data = {
        defunt_nom: document.getElementById('defuntNom').value,
        defunt_prenom: document.getElementById('defuntPrenom').value,
        defunt_date_naissance: document.getElementById('defuntDateNaissance').value,
        defunt_lieu_naissance: document.getElementById('defuntLieuNaissance').value,
        defunt_domicile: document.getElementById('defuntDomicile').value,
        defunt_profession: document.getElementById('defuntProfession').value,
        date_deces: document.getElementById('dateDeces').value,
        heure_deces: document.getElementById('heureDeces').value,
        lieu_deces: document.getElementById('lieuDeces').value,
        cause_deces: document.getElementById('causeDeces').value,
        declarant_nom: document.getElementById('declarantNom').value,
        declarant_prenom: document.getElementById('declarantPrenom').value,
        declarant_qualite: document.getElementById('declarantQualite').value,
        declarant_telephone: document.getElementById('declarantTelephone').value
    };
    
    showNotification('Envoi en cours...', 'info');
    
    try {
        const response = await fetch('http://localhost:8000/api/etat-civil/demandes/deces/', {
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
            showNotification('Erreur lors de l\'envoi', 'error');
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
        color: white; border-radius: 12px; z-index: 9999;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}