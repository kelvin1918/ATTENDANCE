/* idle-timeout.js — auto-logout after a period of no user interaction (mouse,
   keyboard, touch, or scroll). Independent of the fixed session expiry;
   shows a warning countdown before signing out, like most portal logins. */

function initIdleTimeout(opts) {
    opts = opts || {};
    const idleMs   = (opts.idleMinutes || 15) * 60 * 1000;
    const warnMs   = (opts.warnSeconds || 60) * 1000;
    const onLogout = opts.onLogout || function () { window.location.href = '/login?reason=idle'; };

    let idleTimer    = null;
    let countdownInt = null;
    let overlay      = null;
    let lastReset    = 0;

    function buildOverlay() {
        if (overlay) return overlay;

        const style = document.createElement('style');
        style.textContent = `
            #idle-warn-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.55);
                display: flex; align-items: center; justify-content: center; z-index: 99999;
                font-family: 'Segoe UI', sans-serif; }
            #idle-warn-card { background: #fff; border-radius: 16px; padding: 32px 36px;
                max-width: 380px; text-align: center; box-shadow: 0 20px 50px rgba(0,0,0,0.3); }
            #idle-warn-card h3 { margin: 0 0 10px; color: #d32f2f; font-size: 1.1rem; }
            #idle-warn-card p { margin: 0 0 20px; color: #555; font-size: 0.9rem; line-height: 1.5; }
            #idle-warn-count { font-weight: 700; color: #d32f2f; }
            #idle-warn-stay { background: #d32f2f; color: #fff; border: none; border-radius: 10px;
                padding: 12px 26px; font-weight: 700; cursor: pointer; font-size: 0.95rem; }
            #idle-warn-stay:hover { background: #b71c1c; }
        `;
        document.head.appendChild(style);

        overlay = document.createElement('div');
        overlay.id = 'idle-warn-overlay';
        overlay.style.display = 'none';
        overlay.innerHTML = `
            <div id="idle-warn-card">
                <h3>Still there?</h3>
                <p>You've been inactive. For your security, you'll be signed out in
                   <span id="idle-warn-count"></span> seconds.</p>
                <button id="idle-warn-stay">Stay Signed In</button>
            </div>`;
        document.body.appendChild(overlay);
        return overlay;
    }

    function showWarning() {
        buildOverlay();
        overlay.style.display = 'flex';
        let remaining = Math.round(warnMs / 1000);
        const countEl = overlay.querySelector('#idle-warn-count');
        countEl.textContent = remaining;
        clearInterval(countdownInt);
        countdownInt = setInterval(() => {
            remaining--;
            countEl.textContent = remaining;
            if (remaining <= 0) {
                clearInterval(countdownInt);
                overlay.style.display = 'none';
                onLogout();
            }
        }, 1000);
    }

    function hideWarning() {
        if (overlay) overlay.style.display = 'none';
        clearInterval(countdownInt);
    }

    function resetTimer() {
        hideWarning();
        const now = Date.now();
        if (now - lastReset < 1000) return;   // throttle rapid-fire events (mousemove etc.)
        lastReset = now;
        clearTimeout(idleTimer);
        idleTimer = setTimeout(showWarning, idleMs - warnMs);
    }

    ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'click'].forEach(evt => {
        document.addEventListener(evt, resetTimer, { passive: true });
    });

    resetTimer();
}
