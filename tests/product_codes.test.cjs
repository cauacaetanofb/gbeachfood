const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

async function main() {
    const elements = new Map();
    const element = id => {
        if (!elements.has(id)) {
            const classes = new Set();
            elements.set(id, {
                value: '', innerHTML: '', textContent: '', style: {}, files: [], checked: false,
                classList: { add: x => classes.add(x), remove: x => classes.delete(x), contains: x => classes.has(x) },
            });
        }
        return elements.get(id);
    };
    element('form-product').reset = () => {
        for (const [id, input] of elements) if (id.startsWith('p-') || id === 'product-id') input.value = '';
    };
    const products = [
        { id: 1, nome: 'Suco "especial" d\'água <teste>', preco: '7.50', categoria: 'Bebidas',
          descricao: 'Com "aspas"', disponivel: true, sku: 'GBF-0123456789ABCDEF0123456789ABCDEF', ncm: '01012100' },
        { id: 2, nome: 'Café', preco: '3.00', categoria: 'Bebidas', disponivel: false, sku: 'GBF-FEDCBA9876543210FEDCBA9876543210', ncm: '' },
    ];
    const requests = [];
    const toasts = [];
    let failure = false;
    const context = vm.createContext({
        document: { getElementById: element }, FormData, csrftoken: 'test-token',
        apiFetch: async () => ({ products }),
        showToast: (...args) => toasts.push(args),
        fetch: async (url, options) => {
            requests.push({ url, options });
            return { ok: !failure, json: async () => failure ? { error: 'NCM inválido' } : { success: true } };
        },
    });
    const source = fs.readFileSync(path.join(__dirname, '../static/js/dashboard_admin.js'), 'utf8');
    new vm.Script(source, { filename: 'dashboard_admin.js' }).runInContext(context);
    await context.loadProducts();
    assert.ok(element('products-list').innerHTML.includes('SKU: GBF-0123456789ABCDEF'));
    assert.ok(element('products-list').innerHTML.includes('NCM: 01012100'));
    assert.ok(element('products-list').innerHTML.includes('&lt;teste&gt;'));
    assert.ok(element('products-list').innerHTML.includes('onclick="editProduct(1)"'));

    for (const search of ['gbf-012345', '01012100', 'especial']) {
        element('search-product').value = search;
        context.filterProducts();
        assert.ok(element('products-list').innerHTML.includes('editProduct(1)'));
        assert.ok(!element('products-list').innerHTML.includes('editProduct(2)'));
    }
    element('filter-product-cat').value = 'Comidas';
    context.filterProducts();
    assert.ok(element('products-list').innerHTML.includes('Nenhum produto encontrado'));
    element('filter-product-cat').value = '';
    element('search-product').value = '';

    context.editProduct(1);
    assert.equal(element('p-nome').value, products[0].nome);
    assert.equal(element('p-sku').value, products[0].sku);
    assert.equal(element('p-ncm').value, '01012100');
    context.editProduct(2);
    assert.equal(element('p-ncm').value, '');
    context.openAddProduct();
    assert.equal(element('p-sku').value, '');
    assert.equal(element('p-ncm').value, '');

    element('p-nome').value = 'Novo';
    element('p-preco').value = '8.00';
    element('p-ncm').value = '01012100';
    await context.saveProduct({ preventDefault() {} });
    assert.equal(requests[0].url, '/api/products/create/');
    assert.equal(requests[0].options.body.get('ncm'), '01012100');
    assert.equal(requests[0].options.body.has('sku'), false);
    assert.equal(element('modal-product').classList.contains('active'), false);

    context.editProduct(1);
    failure = true;
    await context.saveProduct({ preventDefault() {} });
    assert.deepEqual(toasts.at(-1), ['NCM inválido', 'error']);
    assert.equal(element('modal-product').classList.contains('active'), true);
    assert.equal(element('p-ncm').value, '01012100');
    assert.equal(requests.at(-1).url, '/api/products/1/update/');
    failure = false;
    element('p-ncm').value = '';
    await context.saveProduct({ preventDefault() {} });
    assert.equal(requests.at(-1).options.body.get('ncm'), '');
    assert.equal(element('modal-product').classList.contains('active'), false);
    console.log('OK: códigos, busca, edição, limpeza do NCM e preservação do formulário em erros.');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
