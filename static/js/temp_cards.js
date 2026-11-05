(() => {
    const form = document.getElementById('temp-card-form');
    const fields = document.getElementById('tc-fields');
    const button = document.getElementById('tc-submit');
    const clearButton = document.getElementById('tc-clear');
    const status = document.getElementById('tc-status');
    const storageKey = `gbeachfood.temp-card-pending.${form.dataset.operatorId}`;
    const currency = new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'});
    let pending = null, busy = false;

    function totals() {
        const text = document.getElementById('tc-valor').value;
        const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(text);
        const cents = match ? Number(match[1]) * 100 + Number((match[2] || '').padEnd(2, '0')) : 0;
        const price = Number(pending?.preco_cartao ?? form.dataset.physicalCardPrice);
        const fee = document.getElementById('tc-fisico').checked ? Math.round(price * 100) : 0;
        document.getElementById('tc-physical-label').textContent = `${currency.format(price)} - Incluir cartão físico`;
        document.getElementById('tc-total-saldo').textContent = currency.format(cents / 100);
        document.getElementById('tc-total-fisico').textContent = currency.format(fee / 100);
        document.getElementById('tc-total-cobrar').textContent = currency.format((cents + fee) / 100);
    }
    function clearPending() {
        pending = null;
        try { sessionStorage.removeItem(storageKey); } catch (_) {}
        fields.disabled = false;
        clearButton.disabled = busy;
        button.textContent = 'Criar e imprimir cartão';
    }
    try {
        const saved = JSON.parse(sessionStorage.getItem(storageKey));
        if (saved && typeof saved.request_id === 'string' && typeof saved.nome === 'string'
            && typeof saved.valor === 'string' && typeof saved.incluir_cartao_fisico === 'boolean') {
            pending = saved;
            pending.preco_cartao ??= '2.00';
            for (const field of ['nome', 'cpf', 'telefone', 'valor', 'metodo']) {
                document.getElementById(`tc-${field}`).value = saved[field] || '';
            }
            document.getElementById('tc-fisico').checked = saved.incluir_cartao_fisico;
            fields.disabled = true;
            button.textContent = 'Retomar criação e imprimir cartão';
            status.textContent = 'Há uma criação aguardando confirmação. Retome para recuperar o mesmo cartão, sem repetir a cobrança.';
        }
    } catch (_) {}
    form.addEventListener('input', totals);
    form.addEventListener('physicalpricechange', totals);
    clearButton.disabled = Boolean(pending);
    clearButton.addEventListener('click', () => {
        if (busy || pending) return;
        form.reset();
        document.getElementById('tc-uuid').value = '';
        document.getElementById('temp-card-result').style.display = 'none';
        document.getElementById('tc-qr-img').removeAttribute('src');
        document.getElementById('tc-qr-label').textContent = '';
        document.getElementById('tc-result-summary').textContent = '';
        document.getElementById('tc-print-link').removeAttribute('href');
        totals();
        status.textContent = 'Formulário limpo. Pronto para um novo atendimento.';
        document.getElementById('tc-nome').focus();
    });
    totals();

    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (busy) return;
        if (!pending) {
            if (!form.reportValidity()) return;
            pending = {request_id: crypto.randomUUID(), incluir_cartao_fisico: document.getElementById('tc-fisico').checked,
                preco_cartao: form.dataset.physicalCardPrice};
            for (const field of ['nome', 'cpf', 'telefone', 'valor', 'metodo']) pending[field] = document.getElementById(`tc-${field}`).value;
            try { sessionStorage.setItem(storageKey, JSON.stringify(pending)); } catch (_) {}
        }
        busy = true;
        fields.disabled = true;
        button.disabled = true;
        clearButton.disabled = true;
        status.textContent = 'Criando cartão e preparando a etiqueta...';
        // Aberta pelo clique: evita o bloqueio de pop-up após a resposta da API.
        let printWindow = null;
        try {
            printWindow = window.open('', '_blank');
            if (printWindow) {
                printWindow.opener = null;
                printWindow.document.title = 'Preparando etiqueta — GBeachFood';
                printWindow.document.body.textContent = 'Preparando a etiqueta. Aguarde a confirmação da criação do cartão.';
            }
        } catch (_) {}
        let completed = false;
        try {
            const response = await fetch('/api/cards/temp/create/', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrftoken},
                body: JSON.stringify(pending),
            });
            const data = await response.json();
            if (!response.ok) {
                const error = new Error(data.error || 'Não foi possível criar o cartão.');
                error.status = response.status;
                throw error;
            }
            if (!data.card || !data.card.label_url) throw new Error('Resposta incompleta. Retome a mesma solicitação.');
            completed = true;
            clearPending();
            document.getElementById('temp-card-result').style.display = 'block';
            document.getElementById('tc-qr-img').src = 'data:image/png;base64,' + data.card.qr_code_image;
            document.getElementById('tc-qr-label').textContent = `Cartão de ${data.card.nome} — ${data.card.qr_code_data}`;
            document.getElementById('tc-result-summary').textContent = `Cartão pronto. Saldo inicial: ${currency.format(Number(data.valor_inicial))}. Cartão físico: ${currency.format(Number(data.valor_cartao))}. Total registrado: ${currency.format(Number(data.total_cobrado))}.`;
            document.getElementById('tc-print-link').href = data.card.label_url;
            form.reset();
            document.getElementById('tc-uuid').value = data.card.qr_code_data;
            totals();
            status.textContent = 'Cartão criado. Confira as medidas e escolha a impressora na tela da etiqueta. Se ela não abriu, use Imprimir / reimprimir etiqueta abaixo.';
            if (printWindow && !printWindow.closed) printWindow.location.replace(data.card.label_url);
            showToast('Cartão criado. Etiqueta pronta para impressão.');
        } catch (error) {
            if (printWindow && !printWindow.closed) printWindow.close();
            if (completed) {
                status.textContent = 'O cartão já foi criado. Abra a etiqueta pelo botão abaixo para imprimir.';
            } else if ([400, 403, 404].includes(error.status)) {
                clearPending();
                if (error.status === 400) await refreshCashierPhysicalPrice().catch(() => {});
                status.textContent = error.message;
            } else {
                button.textContent = 'Retomar criação e imprimir cartão';
                status.textContent = 'A criação não foi confirmada. Retome a mesma solicitação para recuperar o cartão sem repetir a cobrança.';
            }
            showToast(error.message, 'error');
        } finally {
            busy = false;
            button.disabled = false;
            clearButton.disabled = Boolean(pending);
        }
    });
})();
