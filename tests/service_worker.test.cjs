const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const handlers = {};
const deleted = [];
let precached;
const context = vm.createContext({
    URL, Response,
    self: {
        location: { origin: 'https://gbeachfood.web.app' },
        addEventListener: (name, fn) => { handlers[name] = fn; },
        skipWaiting() {}, clients: { claim() {} },
    },
    caches: {
        open: async () => ({ addAll: async urls => { precached = urls; }, put: async () => {} }),
        keys: async () => ['gfood-v3', 'gfood-v4', 'gfood-v5', 'gfood-v6', 'gfood-v7', 'unrelated'],
        delete: async key => deleted.push(key),
        match: async () => new Response('offline-static'),
    },
    fetch: async () => new Response('static'),
});
new vm.Script(fs.readFileSync(path.join(__dirname, '../static/sw.js'), 'utf8')).runInContext(context);
(async () => {
    let pending;
    handlers.install({ waitUntil(p) { pending = p; } });
    await pending;
    assert.ok(precached.every(url => url.startsWith('/static/')));
    handlers.activate({ waitUntil(p) { pending = p; } });
    await pending;
    assert.deepEqual(deleted, ['gfood-v3', 'gfood-v4', 'gfood-v5', 'gfood-v6']);
    for (const [method, url] of [
        ['GET', '/'], ['GET', '/login/'], ['GET', '/dashboard/'],
        ['GET', '/api/profile/'], ['POST', '/api/profile/update/'],
        ['POST', '/static/test'], ['GET', 'https://external.example/static/a.js'],
    ]) {
        handlers.fetch({ request: { method, url: new URL(url, 'https://gbeachfood.web.app').href },
            respondWith() { assert.fail('Dynamic or external request intercepted'); } });
    }
    let response;
    handlers.fetch({ request: { method: 'GET', url: 'https://gbeachfood.web.app/static/js/base.js' },
        respondWith(p) { response = p; }, waitUntil() {} });
    assert.equal(await (await response).text(), 'static');
    console.log('OK: PWA caches only static resources and removes old application caches.');
})().catch(error => { console.error(error); process.exitCode = 1; });
