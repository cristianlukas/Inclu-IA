const staticDevIncluIA = "incluIA-v5";

const assets = [
  "/",
  "/static/styles.css",
  "/static/app.js",
  "/static/vendor/socket.io.min.js",
  "/static/manifest.json",
  "/static/favicon.ico",
  "/static/icon-128.png",
  "/static/icon-512.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(staticDevIncluIA).then(cache => cache.addAll(assets))
  );
});

self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) return cachedResponse;
      return fetch(event.request).then((response) => {
        if (!response || response.status !== 200) return response;
        const cloned = response.clone();
        caches.open(staticDevIncluIA).then((cache) => cache.put(event.request, cloned));
        return response;
      });
    })
  );
});

self.addEventListener("activate", event => {
  const whitelist = [staticDevIncluIA];
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.map(key => {
          if (!whitelist.includes(key)) {
            return caches.delete(key);
          }
        })
      )
    )
  );
});
