// Caches the static face shell so the kiosk starts even if the network blips.
// Bump CACHE_VERSION whenever the shell assets change (avoids serving stale faces).
const CACHE_VERSION = 'buddy-shell-v11';
const SHELL = [
  '/app/',
  '/app/index.html',
  '/app/css/face.css',
  '/app/js/face.js',
  '/app/js/state.js',
  '/app/js/audio.js',
  '/app/js/ws-client.js',
  '/app/js/capture-worklet.js',
  '/app/js/app.js',
  '/app/manifest.webmanifest',
  '/app/icon.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_VERSION).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  // Never cache API calls — only the static shell.
  if (request.method !== 'GET' || new URL(request.url).pathname.startsWith('/app/') === false) {
    return;
  }
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request))
  );
});
