/** @odoo-module */
// Este módulo muestra un banner de bienvenida bajo la barra de búsqueda, alineado a la izquierda,
// para administradores y usuarios de solo lectura. El banner se muestra solo una vez por sesión.

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { ListController } from '@web/views/list/list_controller';
import { FormController } from '@web/views/form/form_controller';
import { onMounted } from '@odoo/owl';

// Mapeo nombre de partido -> logo para incrustar en el banner
const PARTY_IMG_MAP = {
    'Partido Liberal Colombiano': '/partidos_politicos/static/src/img/partido_liberal_colombiano.png',
    'Partido Conservador Colombiano': '/partidos_politicos/static/src/img/partido_conservador_colombiano.png',
    'Centro Democrático': '/partidos_politicos/static/src/img/centro_democratico.png',
    'Alianza Verde': '/partidos_politicos/static/src/img/alianza_verde.png',
    'Cambio Radical': '/partidos_politicos/static/src/img/cambio_radical.png',
    'Partido de la U': '/partidos_politicos/static/src/img/partido_delaU.png',
    'Polo Democrático Alternativo': '/partidos_politicos/static/src/img/polo_democratico_alternativo.png',
    'MAIS': '/partidos_politicos/static/src/img/mais.png',
    'MIRA': '/partidos_politicos/static/src/img/mira.png',
    'Comunes': '/partidos_politicos/static/src/img/comunes.png',
    'Colombia Humana': '/partidos_politicos/static/src/img/colombia_humana.png',
    'Dignidad': '/partidos_politicos/static/src/img/dignidad.png',
    'Liga de Gobernantes Anticorrupción': '/partidos_politicos/static/src/img/liga_de_gobernantes_anticorrupcion.png',
};

// Marcador opcional (no bloqueante) para depurar; no se usa para impedir renderizados
window.__ppWelcomeLock = window.__ppWelcomeLock || false;

// Función principal para mostrar el banner de bienvenida si corresponde
async function maybeShowWelcome(ctrl) {
    try {
        const model = ctrl.props.resModel || '';
    // Mostrar el banner en Asignaciones de partido y, para usuarios no admin, también en Mis cargas
    if (model !== 'politico.asignacion' && model !== 'politico.carga') return;

        // Llama al método del modelo para obtener información del usuario actual
        const result = await ctrl.env.services.orm.call(
            'politico.asignacion',
            'get_current_user_assignment',
            [],
            {}
        );
        if (!result) return;

    // Evita duplicados: si ya hay banner, no lo recrees
    if (document.getElementById('pp-welcome-banner')) return;

    // Si es la vista de cargas y el usuario es admin, no mostrar
    if (model === 'politico.carga' && result.is_admin_user) return;

    // Determina el mensaje: admin con texto especial; resto con saludo
        let message = '';
        let adminMode = false;
        if (result.is_admin_user) {
            message = _t('¡Hola administrador! Tienes acceso total a la gestión de partidos políticos.');
            adminMode = true;
        } else {
            const userName = result.user_name || '';
            message = userName ? `Hola, ${userName}` : 'Hola';
        }

    // Asegura limpieza previa (por si fue eliminado externamente)
    const prev = document.getElementById('pp-welcome-banner');
    if (prev) prev.remove();

        // Construye el banner de bienvenida
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
                <div class="pp-welcome-title">${adminMode ? _t('Bienvenido (Administrador)') : ''}</div>
                <div class="pp-welcome-msg">${message}</div>
            </div>`;

    // Coloca el banner antes del área de contenido principal (con pequeño retry si aún no está el DOM)
        const tryPlace = (attempt = 0) => {
            const cp = document.querySelector('.o_control_panel');
            const content = document.querySelector('.o_content');
            if (cp && content && content.parentNode) {
                content.parentNode.insertBefore(banner, content);
            } else if (attempt < 10) {
                setTimeout(() => tryPlace(attempt + 1), 60);
            }
        };
        tryPlace();

    // No eliminar el banner de logo en general; lo usamos en Mis cargas

    // Elimina el banner automáticamente al cambiar de vista
        const removeBanner = () => {
            const b = document.getElementById('pp-welcome-banner');
            if (b) b.remove();
        };
        // Odoo dispara el evento 'hashchange' al cambiar de vista
        window.addEventListener('hashchange', removeBanner, { once: true });

        // Revisión de seguridad para liberar el candado si algo falla
    // Si por alguna razón el DOM se re-renderiza y el banner desaparece,
    // permite que se vuelva a insertar en el próximo setup
    setTimeout(() => { /* noop: ya no usamos lock */ }, 500);
    } catch (_e) {
        // Silencioso ante errores
    }
}

// Parchea el controlador de listas para mostrar el banner solo en Asignaciones de partido
const originalListSetup = ListController.prototype.setup;
patch(ListController.prototype, {
    setup() {
        if (originalListSetup) originalListSetup.call(this, ...arguments);
        if (this.props && (this.props.resModel === 'politico.asignacion' || this.props.resModel === 'politico.carga')) {
            onMounted(() => maybeShowWelcome(this));
        }
    },
});

// Parchea el controlador de formularios para mostrar el banner solo en Asignaciones de partido
const originalFormSetup = FormController.prototype.setup;
patch(FormController.prototype, {
    setup() {
        if (originalFormSetup) originalFormSetup.call(this, ...arguments);
        if (this.props && (this.props.resModel === 'politico.asignacion' || this.props.resModel === 'politico.carga')) {
            onMounted(() => maybeShowWelcome(this));
        }
    },
});
