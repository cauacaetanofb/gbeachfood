function switchTab(name, button) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    document.querySelectorAll('.tab-btn').forEach(b => {
        if (b.getAttribute('onclick').includes(`'${name}'`)) b.classList.add('active');
    });
    if (name === 'saldo') loadExtrato();
}

async function loadMyCard() {
    try {
        const data = await apiFetch('/api/cards/my/');
        document.getElementById('qr-loading').style.display = 'none';
        const img = document.getElementById('my-qr-img');
        img.src = 'data:image/png;base64,' + data.card.qr_code_image;
        img.style.display = data.card.bloqueado ? 'none' : 'block';
        document.getElementById('my-card-status').hidden = !data.card.bloqueado;
        document.getElementById('my-qr-label').textContent = data.card.qr_code_data;
        document.getElementById('my-saldo').textContent = `R$ ${parseFloat(data.card.saldo).toFixed(2)}`;
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function setValor(v) {
    document.getElementById('add-valor').value = v;
}

// ===== Recargas Asaas: PIX e crédito à vista =====
let pixPollingInterval = null;
let currentRecargaId = null;
let pollingVersion = 0;
let criandoRecarga = false;
const formatMoney = value => Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

function atualizarMetodoRecarga() {
    const credito = document.getElementById('add-metodo').value === 'credito';
    document.getElementById('add-valor').min = credito ? '5' : '1';
    document.getElementById('btn-gerar-pix').textContent = credito ? 'Preparar pagamento com cartão' : 'Gerar PIX';
    document.getElementById('recarga-ajuda').textContent = credito
        ? 'Em 1 vez, na página do Asaas. Recarga mínima de R$ 5,00.'
        : 'Pague com QR Code ou PIX copia e cola.';
}

function mostrarEtapaRecarga(id) {
    ['pix-step-1', 'pix-step-2', 'pix-step-3', 'credit-step', 'payment-review'].forEach(name => {
        document.getElementById(name).style.display = name === id ? 'block' : 'none';
    });
    if (id !== 'pix-step-1') document.getElementById('credit-pending').hidden = true;
}

function invoiceUrlSegura(value) {
    try {
        const url = new URL(value);
        return url.protocol === 'https:' && !url.username && !url.password
            && (!url.port || url.port === '443')
            && ['asaas.com', 'www.asaas.com', 'sandbox.asaas.com', 'www.sandbox.asaas.com'].includes(url.hostname);
    } catch (_) { return false; }
}

function mostrarPagamentoCredito(recarga) {
    if (!invoiceUrlSegura(recarga.invoice_url)) throw new Error('Link de pagamento indisponível. Procure o atendimento.');
    document.getElementById('credit-payment-link').href = recarga.invoice_url;
    document.getElementById('credit-valor').textContent = formatMoney(recarga.valor);
    mostrarEtapaRecarga('credit-step');
    iniciarPolling(recarga.recarga_id || recarga.id);
}

async function carregarRecargasPendentes() {
    try {
        const data = await apiFetch('/api/asaas/pending-payments/');
        const list = document.getElementById('credit-pending-list');
        list.replaceChildren();
        for (const recarga of data.recargas) {
            if (!invoiceUrlSegura(recarga.invoice_url)) continue;
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn-secondary';
            btn.textContent = `Continuar recarga de ${formatMoney(recarga.valor)}`;
            btn.addEventListener('click', () => mostrarPagamentoCredito(recarga));
            list.appendChild(btn);
        }
        document.getElementById('credit-pending').hidden = !list.children.length || currentRecargaId !== null;
    } catch (_) { /* A criação de uma nova recarga continua disponível. */ }
}

async function gerarRecarga() {
    if (criandoRecarga) return;
    const valor = document.getElementById('add-valor').value;
    const metodo = document.getElementById('add-metodo').value;
    const minimo = metodo === 'credito' ? 5 : 1;
    if (!valor || !Number.isFinite(Number(valor)) || Number(valor) < minimo) {
        showToast(`Valor mínimo é ${formatMoney(minimo)}`, 'error');
        return;
    }
    criandoRecarga = true;
    const btn = document.getElementById('btn-gerar-pix');
    btn.disabled = true;
    btn.textContent = 'Preparando...';
    try {
        const data = await apiFetch('/api/asaas/create-payment/', {
            method: 'POST', body: JSON.stringify({ valor, metodo })
        });
        if (!data.success) throw new Error(data.error || 'Não foi possível criar a recarga.');
        if (metodo === 'credito') {
            mostrarPagamentoCredito(data);
        } else {
            document.getElementById('pix-qr-img').src = 'data:image/png;base64,' + data.pix_qr_code_image;
            document.getElementById('pix-copia-cola').value = data.pix_copia_cola;
            document.getElementById('pix-valor-display').textContent = formatMoney(data.valor);
            mostrarEtapaRecarga('pix-step-2');
            iniciarPolling(data.recarga_id);
        }
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        criandoRecarga = false;
        btn.disabled = false;
        atualizarMetodoRecarga();
    }
}

function copiarPix() {
    const input = document.getElementById('pix-copia-cola');
    navigator.clipboard.writeText(input.value).then(() => showToast('Código PIX copiado!')).catch(() => {
        input.select();
        document.execCommand('copy');
        showToast('Código PIX copiado!');
    });
}

function iniciarPolling(recargaId) {
    pararPolling();
    currentRecargaId = recargaId;
    const version = pollingVersion;
    async function verificar() {
        if (version !== pollingVersion) return;
        try {
            const data = await apiFetch(`/api/asaas/check-payment/${recargaId}/`);
            if (version !== pollingVersion) return;
            if (data.status === 'pago' || data.status === 'revisao') {
                pararPolling();
                mostrarEtapaRecarga(data.status === 'pago' ? 'pix-step-3' : 'payment-review');
                if (data.status === 'pago') document.getElementById('pix-valor-confirmado').textContent = '+ ' + formatMoney(data.valor);
                loadMyCard();
                return;
            }
        } catch (_) { /* Tenta novamente; nunca presume pagamento pela navegação. */ }
        if (version === pollingVersion) pixPollingInterval = setTimeout(verificar, 3000);
    }
    verificar();
}

function pararPolling() {
    pollingVersion++;
    clearTimeout(pixPollingInterval);
    pixPollingInterval = null;
    currentRecargaId = null;
}

function cancelarPix() {
    pararPolling();
    mostrarEtapaRecarga('pix-step-1');
    document.getElementById('add-valor').value = '';
    carregarRecargasPendentes();
}

function voltarPixInicio() {
    cancelarPix();
    loadExtrato();
}

// ===== Extrato =====
async function loadExtrato() {
    const container = document.getElementById('extrato-list');
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    try {
        const data = await apiFetch('/api/cards/my/transactions/');
        document.getElementById('my-saldo').textContent = `R$ ${parseFloat(data.saldo).toFixed(2)}`;
        if (!data.transactions.length) {
            container.innerHTML = '<div class="empty-state"><p>Nenhuma transação ainda</p></div>';
            return;
        }
        const tipoColors = { deposito: 'var(--success)', pagamento: 'var(--primary)', retirada: 'var(--warning)' };
        const tipoIcons = { deposito: '<svg class="ui-icon" aria-hidden="true" focusable="false"><use href="/static/images/ui-icons.svg#wallet"></use></svg>', pagamento: '<svg class="ui-icon" aria-hidden="true" focusable="false"><use href="/static/images/ui-icons.svg#cart"></use></svg>', retirada: '<svg class="ui-icon" aria-hidden="true" focusable="false"><use href="/static/images/ui-icons.svg#return"></use></svg>' };
        container.innerHTML = data.transactions.map(t => `
            <div style="display:flex;justify-content:space-between;align-items:flex-start;padding:0.7rem 0;border-bottom:1px solid var(--border);">
                <div style="flex:1;min-width:0;">
                    <div style="color:var(--text-primary);font-weight:600;font-size:0.88rem;">
                        ${tipoIcons[t.tipo] || ''} ${t.tipo_label}
                        <span style="color:var(--text-secondary);font-weight:400;font-size:0.75rem;margin-left:0.3rem;">${t.metodo_label}</span>
                    </div>
                    <div style="color:var(--text-secondary);font-size:0.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${t.descricao}</div>
                    <div style="color:var(--text-secondary);font-size:0.72rem;"><svg class="ui-icon" aria-hidden="true" focusable="false"><use href="/static/images/ui-icons.svg#calendar"></use></svg> ${t.data}</div>
                </div>
                <div style="color:${tipoColors[t.tipo] || 'var(--text-primary)'};font-weight:700;font-size:0.9rem;white-space:nowrap;margin-left:0.5rem;">
                    ${t.tipo === 'deposito' ? '+' : '−'} R$ ${parseFloat(t.valor).toFixed(2)}
                </div>
            </div>
        `).join('');
    } catch (e) { showToast(e.message, 'error'); }
}

// Init
loadMyCard();
carregarRecargasPendentes();
atualizarMetodoRecarga();
