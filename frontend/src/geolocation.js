export function initGeolocation(){
    if (!navigator.geolocation) return;
    const tryGeo = () => {
        navigator.geolocation.getCurrentPosition(pos => {
        const { latitude, longitude } = pos.coords;
        const container = document.getElementById('side-panel');
        if (!container) return;
        const div = document.createElement('div');
        div.style.cssText = 'margin-bottom:8px;font-size:11px;color:#8af;';
        div.textContent = `Location: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
        container.insertBefore(div, container.firstChild);
    }, err => {
            console.warn('Geolocation failed', err);
        });
    };
    const onInteraction = () => { tryGeo(); };
    ['click', 'touchstart'].forEach(ev => window.addEventListener(ev, onInteraction, { once: true }));
}
