// frontend/sw.js - Service Worker pour le mode offline
const CACHE_NAME = 'bot-makak-offline-v1';
const urlsToCache = [
    '/',
    '/pages/dechets/index.html',
    '/pages/dechets/signalement.html',
    '/pages/dechets/calendrier.html',
    '/pages/dechets/carte.html',
    '/pages/dechets/tri.html',
    '/pages/dechets/encombrants.html',
    '/css/style.css',
    '/css/activites.css',
    '/js/main.js',
    '/js/modules/dechets.js'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
    );
});

self.addEventListener('sync', event => {
    if (event.tag === 'sync-signalements') {
        event.waitUntil(syncSignalements());
    }
});

async function syncSignalements() {
    const signalementsOffline = await getOfflineSignalements();
    for (const sig of signalementsOffline) {
        try {
            const response = await fetch('/api/dechets/signalements/', {
                method: 'POST',
                body: JSON.stringify(sig),
                headers: { 'Content-Type': 'application/json' }
            });
            if (response.ok) {
                await removeOfflineSignalement(sig.id);
            }
        } catch (error) {
            console.error('Sync failed:', error);
        }
    }
}