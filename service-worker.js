// service-worker.js

const CACHE_NAME = 'prayer-times-global-cache-v1'; // Cache का नाम, संस्करण बदलने पर इसे बदलें
const APP_SHELL_FILES = [
  '/', // Main page
  '/login',
  '/register',
  '/settings',
  '/project/static/css/dist/style.css',
  '/project/static/js/main_script.js',
  '/project/static/js/settings_script.js',
  // '/project/static/js/auth_script.js', // If you create this
  '/project/static/fonts/DS-DIGI.TTF', // या आपके द्वारा चुना गया डिजिटल फॉन्ट
  // Add paths to your app icons if you want them cached for the app shell
  // '/project/static/images/icons/icon-192x192.png',
  // '/project/static/images/icons/icon-512x512.png',
  // Add other essential static assets like a logo if always displayed
  // '/project/static/images/logo.png' 
];

const API_CACHE_NAME = 'prayer-times-api-cache-v1';
const API_BASE_URL = '/api/'; // Our API base URL pattern

// Install event: Cache the app shell
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Install event');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Service Worker] Precaching app shell:', APP_SHELL_FILES);
        return cache.addAll(APP_SHELL_FILES);
      })
      .catch(error => {
        console.error('[Service Worker] Failed to cache app shell during install:', error);
      })
  );
  self.skipWaiting(); // Force the waiting service worker to become the active service worker.
});

// Activate event: Clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activate event');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== API_CACHE_NAME) {
            console.log('[Service Worker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  return self.clients.claim(); // Become available to all pages or clients.
});

// Fetch event: Serve cached content when offline, or fetch from network
self.addEventListener('fetch', (event) => {
  const requestUrl = new URL(event.request.url);

  // Handle API requests: Network first, then cache
  if (requestUrl.pathname.startsWith(API_BASE_URL)) {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          // If successful, clone the response and cache it
          if (networkResponse && networkResponse.ok) {
            const responseToCache = networkResponse.clone();
            caches.open(API_CACHE_NAME)
              .then((cache) => {
                console.log('[Service Worker] Caching API response for:', event.request.url);
                cache.put(event.request, responseToCache);
              });
          }
          return networkResponse;
        })
        .catch(() => {
          // If network fails, try to serve from cache
          console.log('[Service Worker] Network failed for API, trying cache for:', event.request.url);
          return caches.match(event.request)
            .then((cachedResponse) => {
              if (cachedResponse) {
                return cachedResponse;
              }
              // If not in cache, and network failed, return a simple error response for API
              console.warn('[Service Worker] API request not in cache and network failed:', event.request.url);
              return new Response(JSON.stringify({ error: "Offline and data not in cache" }), {
                headers: { 'Content-Type': 'application/json' },
                status: 503, // Service Unavailable
                statusText: "Offline and data not in cache"
              });
            });
        })
    );
  }
  // Handle App Shell and other static asset requests: Cache first, then network
  else if (APP_SHELL_FILES.includes(requestUrl.pathname) || event.request.destination === 'font' || event.request.destination === 'style' || event.request.destination === 'script' || event.request.destination === 'image') {
    event.respondWith(
      caches.match(event.request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            // console.log('[Service Worker] Serving from cache:', event.request.url);
            return cachedResponse;
          }
          // console.log('[Service Worker] Not in cache, fetching from network:', event.request.url);
          return fetch(event.request).then(
            (networkResponse) => {
              // Optionally cache newly fetched static assets if not in APP_SHELL_FILES explicitly
              // For now, only pre-cached assets are served from cache first.
              return networkResponse;
            }
          );
        })
        .catch(error => {
            console.error('[Service Worker] Error in fetch handler for app shell/static assets:', error);
            // You could return a generic offline page here if needed
        })
    );
  }
  // For other requests, just fetch from network (or let browser handle)
  // else {
  //   event.respondWith(fetch(event.request));
  // }
});