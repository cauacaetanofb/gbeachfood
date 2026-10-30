const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const nodes = new Map();
function element() {
    return { style: {}, hidden: true, children: [], value: '', textContent: '',
        replaceChildren() { this.children = []; }, appendChild(node) { this.children.push(node); },
        addEventListener(name, fn) { this[name] = fn; } };
}
function get(id) { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); }
get('add-metodo').value = 'pix';
let paymentStatus = 'pendente', checkOverride, pending = [], createCount = 0, payload;
const errors = [], timers = [];
const context = vm.createContext({
    URL, Number, console,
    document: { getElementById: get, createElement: element, querySelectorAll: () => [] },
    navigator: {}, setTimeout(fn) { timers.push(fn); return timers.length; }, clearTimeout() {},
    showToast(message, type) { errors.push({ message, type }); },
    async apiFetch(url, options) {
        if (url === '/api/cards/my/') return { card: { saldo: '20.00', qr_code_image: 'image', qr_code_data: 'uuid' } };
        if (url === '/api/asaas/pending-payments/') return { recargas: pending };
        if (url === '/api/asaas/create-payment/') {
            createCount++;
            payload = JSON.parse(options.body);
            return { success: true, recarga_id: 7, valor: payload.valor,
                invoice_url: 'https://www.asaas.com/i/test', pix_qr_code_image: 'image', pix_copia_cola: 'code' };
        }
        if (url.startsWith('/api/asaas/check-payment/')) {
            if (checkOverride) return checkOverride;
            return { status: paymentStatus, valor: '20.00' };
        }
        throw new Error('Unexpected API ' + url);
    }
});
new vm.Script(fs.readFileSync(path.join(__dirname, '../static/js/dashboard_cliente.js'), 'utf8')).runInContext(context);
const flush = () => new Promise(resolve => setImmediate(resolve));
(async () => {
    await flush();
    get('add-metodo').value = 'credito';
    context.atualizarMetodoRecarga();
    assert.equal(get('add-valor').min, '5');
    get('add-valor').value = '4.99';
    await context.gerarRecarga();
    assert.equal(createCount, 0);
    get('add-valor').value = '20.00';
    await Promise.all([context.gerarRecarga(), context.gerarRecarga()]);
    await flush();
    assert.equal(createCount, 1);
    assert.deepEqual(payload, { valor: '20.00', metodo: 'credito' });
    assert.equal(get('credit-step').style.display, 'block');
    assert.equal(get('credit-payment-link').href, 'https://www.asaas.com/i/test');
    assert.equal(get('pix-step-3').style.display, 'none');
    paymentStatus = 'pago';
    await timers.pop()();
    assert.equal(get('pix-step-3').style.display, 'block');
    assert.match(get('pix-valor-confirmado').textContent, /20,00/);
    assert.equal(context.invoiceUrlSegura('javascript:alert(1)'), false);
    assert.equal(context.invoiceUrlSegura('https://asaas.com.evil.example/i/test'), false);
    assert.equal(context.invoiceUrlSegura('https://sandbox.asaas.com/i/test'), true);

    pending = [{ id: 9, valor: '30.00', invoice_url: 'https://www.asaas.com/i/pending' }];
    context.cancelarPix();
    await flush();
    assert.equal(get('credit-pending').hidden, false);
    assert.equal(get('credit-pending-list').children.length, 1);
    paymentStatus = 'revisao';
    get('credit-pending-list').children[0].click();
    await flush();
    assert.equal(get('payment-review').style.display, 'block');
    assert.equal(createCount, 1); // Retomar não cria outra cobrança.

    let resolveCheck;
    checkOverride = new Promise(resolve => { resolveCheck = resolve; });
    context.iniciarPolling(10);
    context.cancelarPix();
    resolveCheck({ status: 'pago', valor: '99.00' });
    await flush();
    assert.equal(get('pix-step-1').style.display, 'block'); // Resposta antiga ignorada.
    checkOverride = undefined;
    paymentStatus = 'pendente';
    get('add-metodo').value = 'pix';
    get('add-valor').value = '10.00';
    await context.gerarRecarga();
    assert.equal(get('pix-step-2').style.display, 'block');
    assert.equal(get('pix-copia-cola').value, 'code');
    console.log('OK: crédito, PIX, confirmação por webhook, revisão, retomada, URLs e respostas antigas.');
})().catch(error => { console.error(error); process.exitCode = 1; });
