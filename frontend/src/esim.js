import { fetchJson } from './api.js';
import { API_BASE } from './config.js';

export function initEsim(){
    fetchJson(`${API_BASE}/api/esim/status`)
        .then((data) => {
            const container = document.getElementById('side-panel');
            if (!container) return;
            const div = document.createElement('div');
            div.style.cssText = 'margin-bottom:8px;padding:6px;font-size:11px;color:#6f8;';
            div.innerHTML = `eSIM: ${data.status} | ${data.data_remaining_gb}GB`;
            container.insertBefore(div, container.firstChild);
        })
        .catch(() => {
            const container = document.getElementById('side-panel');
            if (!container) return;
            const div = document.createElement('div');
            div.style.cssText = 'margin-bottom:8px;font-size:11px;color:#864;';
            div.textContent = 'eSIM: unavailable';
            container.insertBefore(div, container.firstChild);
        });
}
