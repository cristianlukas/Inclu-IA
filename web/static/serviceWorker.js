const staticDevIncluIA = "incluIA-v4";

const assets = [
  "/",
  "/static/styles.css",
  "/static/app.js",
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
    caches.match(event.request).then(res => res || fetch(event.request))
  );
});

self.addEventListener("activate", event => {
  const whitelist = ["incluIA-v2"]; // importante actualizar esto
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