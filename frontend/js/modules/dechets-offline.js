// frontend/js/modules/dechets-offline.js
// Gestion des données en mode offline avec IndexedDB

const DB_NAME = 'BotMakakOffline';
const DB_VERSION = 1;
const STORES = {
    SIGNALEMENTS: 'signalements',
    DEMANDES: 'demandes',
    TOURNEES: 'tournees'
};

let db = null;

// Initialiser IndexedDB
function initDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            db = request.result;
            resolve(db);
        };
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            
            if (!db.objectStoreNames.contains(STORES.SIGNALEMENTS)) {
                db.createObjectStore(STORES.SIGNALEMENTS, { keyPath: 'id' });
            }
            if (!db.objectStoreNames.contains(STORES.DEMANDES)) {
                db.createObjectStore(STORES.DEMANDES, { keyPath: 'id' });
            }
            if (!db.objectStoreNames.contains(STORES.TOURNEES)) {
                db.createObjectStore(STORES.TOURNEES, { keyPath: 'id' });
            }
        };
    });
}

// Sauvegarder un signalement pour offline
async function saveSignalementOffline(signalementData) {
    await initDB();
    const transaction = db.transaction([STORES.SIGNALEMENTS], 'readwrite');
    const store = transaction.objectStore(STORES.SIGNALEMENTS);
    
    const offlineData = {
        id: crypto.randomUUID(),
        ...signalementData,
        timestamp: new Date().toISOString(),
        synced: false
    };
    
    return new Promise((resolve, reject) => {
        const request = store.add(offlineData);
        request.onsuccess = () => resolve(offlineData.id);
        request.onerror = () => reject(request.error);
    });
}

// Récupérer tous les signalements non synchronisés
async function getOfflineSignalements() {
    await initDB();
    const transaction = db.transaction([STORES.SIGNALEMENTS], 'readonly');
    const store = transaction.objectStore(STORES.SIGNALEMENTS);
    
    return new Promise((resolve, reject) => {
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result.filter(s => !s.synced));
        request.onerror = () => reject(request.error);
    });
}

// Marquer un signalement comme synchronisé
async function markSignalementSynced(id) {
    await initDB();
    const transaction = db.transaction([STORES.SIGNALEMENTS], 'readwrite');
    const store = transaction.objectStore(STORES.SIGNALEMENTS);
    
    const signalement = await new Promise((resolve) => {
        const getRequest = store.get(id);
        getRequest.onsuccess = () => resolve(getRequest.result);
    });
    
    if (signalement) {
        signalement.synced = true;
        store.put(signalement);
    }
}

// Sauvegarder une tournée pour offline (agent)
async function saveTourneeOffline(tourneeData) {
    await initDB();
    const transaction = db.transaction([STORES.TOURNEES], 'readwrite');
    const store = transaction.objectStore(STORES.TOURNEES);
    
    const offlineData = {
        ...tourneeData,
        synced: false,
        timestamp: new Date().toISOString()
    };
    
    return new Promise((resolve, reject) => {
        const request = store.put(offlineData);
        request.onsuccess = () => resolve(offlineData.id);
        request.onerror = () => reject(request.error);
    });
}

// Mettre à jour un point de collecte dans une tournée offline
async function updateTourneePointOffline(tourneeId, pointId, data) {
    await initDB();
    const transaction = db.transaction([STORES.TOURNEES], 'readwrite');
    const store = transaction.objectStore(STORES.TOURNEES);
    
    const tournee = await new Promise((resolve) => {
        const getRequest = store.get(tourneeId);
        getRequest.onsuccess = () => resolve(getRequest.result);
    });
    
    if (tournee) {
        const point = tournee.points.find(p => p.id === pointId);
        if (point) {
            Object.assign(point, data);
            store.put(tournee);
        }
    }
}

// Synchronisation automatique quand la connexion revient
window.addEventListener('online', async () => {
    console.log('Connexion rétablie, synchronisation...');
    
    // Synchroniser les signalements
    const signalements = await getOfflineSignalements();
    for (const sig of signalements) {
        try {
            const response = await fetch('/api/dechets/signalements/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                },
                body: JSON.stringify(sig.data)
            });
            
            if (response.ok) {
                await markSignalementSynced(sig.id);
                showToast('Signalements synchronisés', 'success');
            }
        } catch (error) {
            console.error('Sync error:', error);
        }
    }
    
    // Synchroniser les tournées (agent)
    // ...
});

// Vérifier si on est en mode offline
function isOffline() {
    return !navigator.onLine;
}

// Enregistrer le service worker
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
        .then(reg => console.log('Service Worker registered', reg))
        .catch(err => console.error('Service Worker error', err));
}

// Enregistrer pour synchronisation en arrière-plan
if ('SyncManager' in window) {
    navigator.serviceWorker.ready.then(reg => {
        reg.sync.register('sync-signalements');
    });
}

// Exporter
window.offlineDechets = {
    saveSignalementOffline,
    getOfflineSignalements,
    saveTourneeOffline,
    updateTourneePointOffline,
    isOffline,
    initDB
};