/** @odoo-module */
// Muestra una notificación de bienvenida sólo a usuarios del grupo de solo lectura
// cuando visitan el modelo politico.carga. Se muestra una vez por sesión y por usuario.

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { ListController } from '@web/views/list/list_controller';
import { FormController } from '@web/views/form/form_controller';

async function maybeShowWelcome(ctrl) {
    try {
        // Limitar al modelo de cargas
        if (ctrl.props.resModel !== 'politico.carga') return;

        const result = await ctrl.env.services.orm.call(
            'politico.asignacion',
            'get_current_user_assignment',
            [],
            {}
        );
        if (!result || !result.is_readonly_user) return; // Nunca mostrar a administradores

        const storageKey = `pp_welcome_shown_${result.user_id || '0'}`;
        if (sessionStorage.getItem(storageKey) === '1') return;

        const userName = result.user_name || '';
        const partido = result.partido_name || _t('Sin asignar');
        const message = userName
            ? _t('Hola %s, tu partido político es: %s').replace('%s', userName).replace('%s', partido)
            : _t('Hola, tu partido político es: %s').replace('%s', partido);
        setTimeout(() => {
            ctrl.env.services.notification.add(message, {
                title: _t('Bienvenido'),
                type: 'success',
                sticky: false,
            });
        }, 150);
        sessionStorage.setItem(storageKey, '1');
    } catch (_e) {
        // Silenciar errores para no bloquear la interfaz
    }
}

const originalListSetup = ListController.prototype.setup;
patch(ListController.prototype, {
    setup() {
        if (originalListSetup) {
            originalListSetup.call(this, ...arguments);
        }
        maybeShowWelcome(this);
    },
});

const originalFormSetup = FormController.prototype.setup;
patch(FormController.prototype, {
    setup() {
        if (originalFormSetup) {
            originalFormSetup.call(this, ...arguments);
        }
        maybeShowWelcome(this);
    },
});
