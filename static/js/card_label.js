(() => {
    const form = document.getElementById('label-settings');
    const width = document.getElementById('label-width');
    const height = document.getElementById('label-height');
    const button = document.getElementById('print-label');
    const status = document.getElementById('label-status');
    const qr = document.getElementById('label-qr');
    const storageKey = 'gbeachfood.label-size';
    try {
        const saved = JSON.parse(localStorage.getItem(storageKey));
        if (saved && Number.isInteger(saved.width) && saved.width >= 40 && saved.width <= 100
            && Number.isInteger(saved.height) && saved.height >= 30 && saved.height <= 100) {
            width.value = saved.width; height.value = saved.height;
        }
    } catch (_) {}
    function updateSize() {
        if (!form.checkValidity()) return false;
        const w = Number(width.value), h = Number(height.value);
        document.documentElement.style.setProperty('--label-width', `${w}mm`);
        document.documentElement.style.setProperty('--label-height', `${h}mm`);
        document.documentElement.style.setProperty('--qr-size', `${Math.min(w - 4, h - 13, 40)}mm`);
        document.getElementById('label-page-size').textContent = `@page { size: ${w}mm ${h}mm; margin: 0; }`;
        try { localStorage.setItem(storageKey, JSON.stringify({width: w, height: h})); } catch (_) {}
        return true;
    }
    form.addEventListener('input', updateSize);
    form.addEventListener('submit', event => {
        event.preventDefault();
        if (!qr.naturalWidth || !updateSize()) return;
        status.textContent = 'Selecione a impressora na janela de impressão. Se precisar, você pode imprimir esta etiqueta novamente.';
        window.print();
    });
    function ready() {
        button.disabled = false;
        status.textContent = 'QR Code pronto. Confira as medidas da etiqueta antes de imprimir.';
    }
    qr.addEventListener('load', ready);
    qr.addEventListener('error', () => { status.textContent = 'Falha ao carregar o QR Code. Recarregue esta página para tentar novamente.'; });
    updateSize();
    if (qr.complete && qr.naturalWidth) ready();
})();
