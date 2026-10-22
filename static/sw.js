// Service Worker — GFood PWA
const CACHE_NAME = 'gfood-v5';

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll([
            '/static/css/custom.css',
            '/static/js/base.js',
        ]))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.filter(key => key.startsWith('gfood-') && key !== CACHE_NAME)
                .map(key => caches.delete(key))
        )).then(() => self.clients.claim())
    );
});

// Somente estáticos: páginas com tokens CSRF, dados pessoais e APIs usam a rede.
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    if (event.request.method !== 'GET' || url.origin !== self.location.origin
        || !url.pathname.startsWith('/static/')) return;

    event.respondWith(
        fetch(event.request).then(response => {
            if (response.ok) {
                const clone = response.clone();
                event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone)));
            }
            return response;
        }).catch(async () => (await caches.match(event.request)) || Response.error())
    );
});
