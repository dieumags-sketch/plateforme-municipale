/**
 * MODULE ÉTAT CIVIL - ACTE DE RECONNAISSANCE
 */

let currentStep = 1;
const totalSteps = 3;

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
            return validateRequired(['enfantNom', 'enfantPrenom', 'enfantDateNaissance', 'enfantLieuNaissance']);
        case 2:
            return validateRequired(['parentNom', 'parentPrenom', 'parentDateNaissance', 'parentLieuNaissance']);
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
            <h4>👶 Enfant</h4>
            <p><strong>Nom:</strong> ${document.getElementById('enfantNom').value} ${document.getElementById('enfantPrenom').value}</p>
            <p><strong>Né le:</strong> ${document.getElementById('enfantDateNaissance').value}</p>
            <p><strong>Lieu:</strong> ${document.getElementById('enfantLieuNaissance').value}</p>
        </div>
        <div class="recap-section">
            <h4>👨‍👩 Parent reconnaissant</h4>
            <p><strong>Nom:</strong> ${document.getElementById('parentNom').value} ${document.getElementById('parentPrenom').value}</p>
            <p><strong>Né le:</strong> ${document.getElementById('parentDateNaissance').value}</p>
            <p><strong>Tél:</strong> ${document.getElementById('parentTelephone').value || 'Non renseigné'}</p>
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
        enfant_nom: document.getElementById('enfantNom').value,
        enfant_prenom: document.getElementById('enfantPrenom').value,
        enfant_date_naissance: document.getElementById('enfantDateNaissance').value,
        enfant_lieu_naissance: document.getElementById('enfantLieuNaissance').value,
        enfant_mere_nom: document.getElementById('mereNom').value,
        parent_nom: document.getElementById('parentNom').value,
        parent_prenom: document.getElementById('parentPrenom').value,
        parent_date_naissance: document.getElementById('parentDateNaissance').value,
        parent_lieu_naissance: document.getElementById('parentLieuNaissance').value,
        parent_domicile: document.getElementById('parentDomicile').value,
        parent_profession: document.getElementById('parentProfession').value,
        parent_telephone: document.getElementById('parentTelephone').value
    };
    
    showNotification('Envoi en cours...', 'info');
    
    try {
        const response = await fetch('http://localhost:8000/api/etat-civil/demandes/reconnaissance/', {
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