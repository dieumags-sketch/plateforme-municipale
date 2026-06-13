/**
 * PAGE REÇU DE PAIEMENT
 */

const API_URL = 'http://localhost:8000/api/paiements';

// Récupérer l'ID de la transaction dans l'URL
const urlParams = new URLSearchParams(window.location.search);
const transactionId = urlParams.get('id');

document.addEventListener('DOMContentLoaded', async () => {
    if (!transactionId) {
        showError('Aucune transaction spécifiée');
        return;
    }
    
    await chargerRecu();
});

async function chargerRecu() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '../accounts/login.html';
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/transactions/${transactionId}/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) throw new Error('Transaction non trouvée');
        
        const transaction = await response.json();
        
        // Remplir les champs
        document.getElementById('recuNumero').textContent = `REC-${transaction.reference}`;
        document.getElementById('recuDate').textContent = new Date(transaction.date_creation).toLocaleString('fr-FR');
        document.getElementById('recuNom').textContent = transaction.utilisateur_nom || 'Citoyen';
        document.getElementById('recuEmail').textContent = transaction.utilisateur_email || '-';
        document.getElementById('recuReference').textContent = transaction.reference;
        document.getElementById('recuMode').textContent = transaction.mode_display;
        document.getElementById('recuDatePaiement').textContent = transaction.date_confirmation ? new Date(transaction.date_confirmation).toLocaleString('fr-FR') : new Date(transaction.date_creation).toLocaleString('fr-FR');
        
        const services = {
            'etat_civil': '🏛️ État Civil',
            'activites': '🎯 Activités municipales',
            'dechets': '🗑️ Gestion des déchets',
            'archives': '📚 Archives municipales',
            'amendes': '⚠️ Amendes',
            'taxes': '🏠 Taxes municipales'
        };
        document.getElementById('recuService').textContent = services[transaction.module_source] || transaction.module_source;
        document.getElementById('recuSourceId').textContent = transaction.source_id || '-';
        
        document.getElementById('recuNet').textContent = `${transaction.montant_net.toLocaleString()} FCFA`;
        document.getElementById('recuFrais').textContent = `${transaction.frais.toLocaleString()} FCFA`;
        document.getElementById('recuTaxe').textContent = `${transaction.taxe.toLocaleString()} FCFA`;
        document.getElementById('recuTotal').textContent = `${transaction.montant_total.toLocaleString()} FCFA`;
        document.getElementById('recuTransactionId').textContent = transaction.numero_transaction || transaction.reference;
        
        // Générer QR code
        genererQRCode(transaction.reference);
        
    } catch (error) {
        showError('Erreur lors du chargement du reçu');
    }
}

function genererQRCode(data) {
    // Utilisation de l'API QR code
    const qrContainer = document.getElementById('qrcode');
    qrContainer.innerHTML = `<img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(data)}" alt="QR Code">`;
}

function imprimerRecu() {
    window.print();
}

function showError(message) {
    document.getElementById('recuContent').innerHTML = `
        <div style="text-align: center; padding: 60px;">
            <i class="fas fa-exclamation-triangle" style="font-size: 60px; color: #ef4444;"></i>
            <p style="margin-top: 20px;">${message}</p>
            <button class="btn-primary" onclick="window.location.href='historique.html'">Retour à l'historique</button>
        </div>
    `;
}