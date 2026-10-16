const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');

async function checkRecovery(formToken) {
    const elements = new Map();
    function element(id) {
        if (!elements.has(id)) elements.set(id, {
            style: {}, value: '', textContent: '',
            classList: { add() {}, remove() {} },
        });
        return elements.get(id);
    }
    const requests = [];
    let fail = false;
    const context = vm.createContext({
        document: {
            cookie: 'csrftoken=cookie-token',
            querySelector: () => formToken ? { value: formToken } : null,
            getElementById: element,
            addEventListener() {},
        },
        navigator: {},
        window: { addEventListener() {}, matchMedia: () => ({ matches: false }), navigator: {} },
        fetch: async (url, options) => {
            requests.push({ url, options });
            return { ok: !fail, json: async () => fail ? { error: 'Envio indisponível' } : { success: true } };
        },
    });
    const base = fs.readFileSync(path.join(root, 'static/js/base.js'), 'utf8');
    const template = fs.readFileSync(path.join(root, 'templates/login.html'), 'utf8');
    // Reproduz a ordem dos scripts clássicos no mesmo contexto global do navegador.
    new vm.Script(base, { filename: 'base.js' }).runInContext(context);
    for (const match of template.matchAll(/<script>([\s\S]*?)<\/script>/g)) {
        new vm.Script(match[1], { filename: 'login.html' }).runInContext(context);
    }
    context.showForgotStep(1);
    assert.equal(element('forgot-step-1').style.display, 'block');
    element('fg-email').value = 'cliente@example.com';
    await context.sendResetCode();
    assert.equal(element('forgot-step-2').style.display, 'block');
    assert.equal(requests[0].url, '/api/forgot-password/');
    assert.equal(requests[0].options.headers['X-CSRFToken'], formToken || 'cookie-token');
    element('fg-code').value = '123456';
    element('fg-new-pass').value = 'NovaSenha123!';
    element('fg-new-pass2').value = 'NovaSenha123!';
    await context.resetPassword();
    assert.equal(element('forgot-step-3').style.display, 'block');
    assert.equal(requests[1].url, '/api/reset-password/');
    assert.equal(JSON.parse(requests[1].options.body).code, '123456');
    fail = true;
    context.showForgotStep(1);
    await context.sendResetCode();
    assert.equal(element('forgot-step-1').style.display, 'block');
    assert.equal(element('fg-toast').textContent, 'Envio indisponível');
}

(async () => {
    await checkRecovery('form-token');
    await checkRecovery(null);
    console.log('OK: scripts, modal, CSRF, envio, redefinição e erro de recuperação.');
})().catch(error => { console.error(error); process.exitCode = 1; });
