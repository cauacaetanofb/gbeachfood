function getCookie(name) {
    let val = null;
    document.cookie.split(';').forEach(c => {
        c = c.trim();
        if (c.startsWith(name + '=')) val = decodeURIComponent(c.substring(name.length + 1));
    });
    return val;
}
const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || getCookie('csrftoken');

function showToast(msg, type = 'success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast show ' + type;
    setTimeout(() => t.className = 'toast', 3000);
}

async function apiFetch(url, options = {}) {
    const defaults = {
        headers: {
            'X-CSRFToken': csrftoken,
        },
        credentials: 'same-origin',
    };
    if (options.body && !(options.body instanceof FormData)) {
        defaults.headers['Content-Type'] = 'application/json';
    }
    const res = await fetch(url, { ...defaults, ...options, headers: { ...defaults.headers, ...(options.headers || {}) } });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || 'Erro na requisição');
    }
    return data;
}

// ========= PWA: Service Worker + Install Prompt =========

// Registra o Service Worker
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
        .then(reg => console.log('SW registrado:', reg.scope))
        .catch(err => console.log('SW falhou:', err));
}

// Captura o evento de instalação do navegador
let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
    // Impede o mini-banner padrão do Chrome
    e.preventDefault();
    // Guarda o evento para usar depois
    deferredPrompt = e;
});

// Função chamada quando o usuário clica no botão "Instale o app"
function installApp() {
    if (!deferredPrompt) {
        // Fallback para navegadores que não suportam o prompt nativo
        showToast('Abra o menu do navegador e toque em "Adicionar à tela inicial"');
        return;
    }
    // Dispara o prompt nativo de instalação
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(result => {
        if (result.outcome === 'accepted') {
            showToast('App instalado com sucesso! 🎉');
        }
        deferredPrompt = null;
        const banner = document.getElementById('install-banner');
        if (banner) banner.style.display = 'none';
    });
}

// Esconde o botão se o app já estiver instalado (modo standalone)
window.addEventListener('appinstalled', () => {
    const banner = document.getElementById('install-banner');
    if (banner) banner.style.display = 'none';
    deferredPrompt = null;
});

// Se já está rodando como app instalado, esconde o botão
if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone) {
    document.addEventListener('DOMContentLoaded', () => {
        const banner = document.getElementById('install-banner');
        if (banner) banner.style.display = 'none';
    });
}

// ========= Imprimir Relatório =========
function printReport(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    const now = new Date();
    const dataHora = now.toLocaleDateString('pt-BR') + ' às ' + now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

    // Clonar conteúdo e limpar elementos interativos
    const clone = el.cloneNode(true);
    clone.querySelectorAll('button, input, select, .period-select, .loading').forEach(e => e.remove());
    // Limpar estilos de cor para impressão P&B
    clone.querySelectorAll('[style]').forEach(e => {
        e.style.color = '#111';
        e.style.background = 'transparent';
        e.style.backgroundColor = 'transparent';
        e.style.borderColor = '#ddd';
    });

    const html = '<!DOCTYPE html><html lang="pt-br"><head><meta charset="UTF-8"><title>GFood — Relatório</title>' +
        '<style>' +
        '* { margin:0; padding:0; box-sizing:border-box; }' +
        'body { font-family: "Segoe UI", Arial, sans-serif; color:#111; padding:20px; font-size:13px; }' +
        '.print-header { text-align:center; margin-bottom:20px; border-bottom:2px solid #333; padding-bottom:12px; }' +
        '.print-header h1 { font-size:22px; margin-bottom:2px; }' +
        '.print-header .date { color:#666; font-size:12px; }' +
        'table { width:100%; border-collapse:collapse; margin:8px 0; }' +
        'th, td { padding:6px 8px; text-align:left; border-bottom:1px solid #ddd; font-size:12px; }' +
        'th { background:#f5f5f5; font-weight:700; }' +
        'h3 { font-size:14px; margin:14px 0 6px; }' +
        '</style></head><body>' +
        '<div class="print-header"><h1>GFood</h1><div class="date">Relatório gerado em ' + dataHora + '</div></div>' +
        clone.innerHTML +
        '</body></html>';

    const printWindow = window.open('', '_blank', 'width=800,height=600');
    if (!printWindow) {
        showToast('Permita popups para imprimir o relatório', 'error');
        return;
    }
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.onload = function() {
        printWindow.print();
    };
}
