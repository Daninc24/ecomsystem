/**
 * Service Worker for Mobile Admin Interface
 * Handles push notifications, offline caching, and background sync
 */

const CACHE_NAME = 'mobile-admin-v1';
const urlsToCache = [
    '/',
    '/admin/dashboard',
    '/static/css/mobile-admin.css',
    '/static/js/mobile-admin.js',
    '/static/images/favicon-32x32.png',
    '/static/images/favicon-16x16.png'
];

// Install event - cache resources
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Return cached version or fetch from network
                if (response) {
                    return response;
                }
                return fetch(event.request);
            })
    );
});

// Push event - handle push notifications
self.addEventListener('push', (event) => {
    console.log('Push event received:', event);
    
    let notificationData = {};
    
    if (event.data) {
        try {
            notificationData = event.data.json();
        } catch (e) {
            notificationData = {
                title: 'Admin Notification',
                body: event.data.text() || 'You have a new notification',
                icon: '/static/images/favicon-32x32.png',
                badge: '/static/images/favicon-16x16.png'
            };
        }
    }
    
    const options = {
        body: notificationData.body || 'You have a new notification',
        icon: notificationData.icon || '/static/images/favicon-32x32.png',
        badge: notificationData.badge || '/static/images/favicon-16x16.png',
        vibrate: notificationData.vibrate || [200, 100, 200],
        data: {
            url: notificationData.url || '/admin/dashboard',
            timestamp: Date.now(),
            ...notificationData.data
        },
        actions: notificationData.actions || [
            {
                action: 'view',
                title: 'View',
                icon: '/static/images/favicon-16x16.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss'
            }
        ],
        requireInteraction: notificationData.priority === 'high',
        silent: notificationData.silent || false,
        tag: notificationData.tag || 'admin-notification'
    };
    
    event.waitUntil(
        self.registration.showNotification(
            notificationData.title || 'Admin Notification',
            options
        )
    );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
    console.log('Notification click received:', event);
    
    event.notification.close();
    
    if (event.action === 'dismiss') {
        return;
    }
    
    const urlToOpen = event.notification.data.url || '/admin/dashboard';
    
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then((clientList) => {
            // Check if there's already a window/tab open with the target URL
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            
            // If no window/tab is open, open a new one
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});

// Background sync event
self.addEventListener('sync', (event) => {
    console.log('Background sync event:', event);
    
    if (event.tag === 'admin-data-sync') {
        event.waitUntil(syncAdminData());
    }
});

// Sync offline admin data
async function syncAdminData() {
    try {
        // Get offline data from IndexedDB or localStorage
        const offlineData = await getOfflineData();
        
        if (offlineData.length > 0) {
            const response = await fetch('/api/admin/mobile/sync-offline-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(offlineData)
            });
            
            if (response.ok) {
                await clearOfflineData();
                console.log('Offline data synced successfully');
                
                // Show success notification
                self.registration.showNotification('Data Synced', {
                    body: 'Your offline changes have been synced successfully',
                    icon: '/static/images/favicon-32x32.png',
                    tag: 'sync-success'
                });
            }
        }
    } catch (error) {
        console.error('Failed to sync offline data:', error);
        
        // Show error notification
        self.registration.showNotification('Sync Failed', {
            body: 'Failed to sync offline changes. Will retry later.',
            icon: '/static/images/favicon-32x32.png',
            tag: 'sync-error'
        });
    }
}

// Get offline data (placeholder - would use IndexedDB in real implementation)
async function getOfflineData() {
    // In a real implementation, this would read from IndexedDB
    return [];
}

// Clear offline data (placeholder - would use IndexedDB in real implementation)
async function clearOfflineData() {
    // In a real implementation, this would clear IndexedDB
    return true;
}

// Handle message from main thread
self.addEventListener('message', (event) => {
    console.log('Service worker received message:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'SYNC_DATA') {
        // Trigger background sync
        self.registration.sync.register('admin-data-sync');
    }
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

console.log('Mobile Admin Service Worker loaded');