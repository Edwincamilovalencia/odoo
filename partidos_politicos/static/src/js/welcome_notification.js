/** @odoo-module */
// Muestra un banner de bienvenida bajo la barra de búsqueda, alineado a la izquierda,
// para administradores y usuarios de solo lectura. Una vez por sesión.

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { ListController } from '@web/views/list/list_controller';
import { FormController } from '@web/views/form/form_controller';

// Global lock to avoid multiple banners racing between List/Form controllers
window.__ppWelcomeLock = window.__ppWelcomeLock || false;

async function maybeShowWelcome(ctrl) {
    try {
        const model = ctrl.props.resModel || '';

        const result = await ctrl.env.services.orm.call(
            'politico.asignacion',
            'get_current_user_assignment',
            [],
            {}
        );
        if (!result) return;

        const storageKey = `pp_welcome_shown_${result.user_id || '0'}`;
        if (sessionStorage.getItem(storageKey) === '1') return;
        if (window.__ppWelcomeLock) return;

        // Determine where to show depending on role
        let message = '';
        let adminMode = false;
        let shouldShow = false;
        if (result.is_admin_user && model === 'politico.asignacion') {
            message = _t('¡Hola administrador! Tienes acceso total a la gestión de partidos políticos.');
            adminMode = true;
            shouldShow = true;
        } else if (result.is_readonly_user && model === 'politico.carga') {
            const userName = result.user_name || '';
            const partido = result.partido_name || _t('Sin asignar');
            message = userName ? `Hola ${userName}, tu partido político es: ${partido}` : `Hola, tu partido político es: ${partido}`;
            shouldShow = true;
        }
        if (!shouldShow) return;

        window.__ppWelcomeLock = true;
        const injectWhenStable = (attempt = 0) => {
            // Clean any previous banner
            const prev = document.getElementById('pp-welcome-banner');
            if (prev) prev.remove();

            const cp = document.querySelector('.o_control_panel');
            const content = document.querySelector('.o_content');

            // Wait for required anchors depending on role
            if (adminMode) {
                if (!cp || !content) {
                    if (attempt < 20) return setTimeout(() => injectWhenStable(attempt + 1), 100);
                    window.__ppWelcomeLock = false; return;
                }
            } else {
                const needParty = model === 'politico.carga';
                const party = document.getElementById('pp_party_banner');
                if (!cp || (needParty && !party)) {
                    if (attempt < 20) return setTimeout(() => injectWhenStable(attempt + 1), 100);
                    window.__ppWelcomeLock = false; return;
                }
            }

            // Build banner
            const banner = document.createElement('div');
            banner.id = 'pp-welcome-banner';
            banner.className = 'pp-welcome-banner' + (adminMode ? ' pp-welcome-admin' : '');
            banner.innerHTML = `
                <span class="pp-welcome-icon" aria-hidden="true">
                    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="14" cy="14" r="14" fill="${adminMode ? '#e3f2fd' : '#e8f5e9'}"/>
                        ${adminMode
                            ? '<path d="M14 8v4m0 4h.01" stroke="#1976d2" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
                            : '<path d="M9.5 14.5L13 18L19 12" stroke="#27ae60" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'}
                    </svg>
                </span>
                <div class="pp-welcome-content">
                    <div class="pp-welcome-title">${adminMode ? _t('Bienvenido (Administrador)') : _t('Bienvenido')}</div>
                    <div class="pp-welcome-msg">${message}</div>
                </div>`;

            if (adminMode) {
                // Admin: place directly before the content area
                content.parentNode.insertBefore(banner, content);
            } else {
                // Readonly: place before party banner or just after control panel
                const partyNow = document.getElementById('pp_party_banner');
                if (partyNow && partyNow.parentNode) {
                    partyNow.parentNode.insertBefore(banner, partyNow);
                } else if (cp) {
                    const bottom = cp.querySelector('.o_cp_bottom');
                    const top = cp.querySelector('.o_cp_top');
                    if (bottom) bottom.insertAdjacentElement('afterend', banner);
                    else if (top) top.insertAdjacentElement('afterend', banner);
                    else cp.parentNode.insertBefore(banner, cp.nextSibling);
                }
            }

            // Mark shown after a small delay to avoid race with late re-renders
            setTimeout(() => sessionStorage.setItem(storageKey, '1'), 600);
            setTimeout(() => banner.classList.add('pp-welcome-hide'), 4800);
            setTimeout(() => banner.remove(), 5600);

            // Safety recheck
            setTimeout(() => {
                if (!document.getElementById('pp-welcome-banner') && attempt < 5) {
                    injectWhenStable(attempt + 1);
                } else {
                    window.__ppWelcomeLock = false;
                }
            }, 500);
        };
        setTimeout(() => injectWhenStable(0), 120);
    } catch (_e) {
        // silent
    }
}

const originalListSetup = ListController.prototype.setup;
patch(ListController.prototype, {
    setup() {
        if (originalListSetup) originalListSetup.call(this, ...arguments);
        // Forzar mensaje admin en politico.asignacion (tree)
        if (this.props && this.props.resModel === 'politico.asignacion') {
            maybeShowWelcome(this);
        } else if (this.props && this.props.resModel === 'politico.carga') {
            maybeShowWelcome(this);
        }
    },
});

const originalFormSetup = FormController.prototype.setup;
patch(FormController.prototype, {
    setup() {
        if (originalFormSetup) originalFormSetup.call(this, ...arguments);
        // Forzar mensaje admin en politico.asignacion (form)
        if (this.props && this.props.resModel === 'politico.asignacion') {
            maybeShowWelcome(this);
        } else if (this.props && this.props.resModel === 'politico.carga') {
            maybeShowWelcome(this);
        }
    },
});
