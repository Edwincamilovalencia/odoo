
/** @odoo-module */
import { ListController } from '@web/views/list/list_controller';
import { patch } from '@web/core/utils/patch';
import { onMounted } from '@odoo/owl';

// Propósito: Para usuarios de solo lectura en la vista de lista de politico.carga ("Mi Partido"),
// renderiza un banner centrado con el logo del partido justo debajo de la barra de búsqueda.
// El banner muestra el logo del partido asignado al usuario actual (politico.asignacion -> partido_id).
// Si el usuario no tiene asignación, no se muestra ningún banner.


// Mapeo de nombre de partido a la ruta de la imagen correspondiente
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

// Guarda la referencia al método original setup del ListController
const _superSetup = ListController.prototype.setup;

patch(ListController.prototype, {
    setup() {
        _superSetup.call(this, ...arguments);
        // Solo aplica en la vista de lista de politico.carga
        if (!(this.props && this.props.resModel === 'politico.carga')) return;

        this.orm = this.env.services.orm;
        const user = this.env.services.user;

        // Determina si el usuario es solo lectura (no admin)
        this._ppIsAdminPromise = Promise.resolve(false);
        try {
            if (user && user.hasGroup) {
                const r = user.hasGroup('base.group_system');
                this._ppIsAdminPromise = (r && typeof r.then === 'function') ? r : Promise.resolve(!!r);
            }
        } catch (_) {}

        // Cuando el componente está montado, verifica si debe mostrar el banner
        onMounted(() => {
            (this._ppIsAdminPromise || Promise.resolve(false)).then(async (isAdmin) => {
                if (isAdmin) return; // Solo los usuarios de solo lectura deben ver el banner
                try {
                    // Busca el partido asignado al usuario actual mediante politico.asignacion
                    const asignRows = await this.orm.searchRead(
                        'politico.asignacion',
                        [['user_id', '=', this.env.services.user.userId]],
                        ['partido_id'],
                        { limit: 1 }
                    );
                    const partidoName = (asignRows && asignRows[0] && asignRows[0].partido_id && asignRows[0].partido_id[1]) || null;
                    if (!partidoName) return;

                    const imgUrl = PARTY_IMG_MAP[partidoName];
                    if (!imgUrl) return;

                    // Inyecta el banner con el logo del partido
                    this._injectPartyBanner(imgUrl, partidoName);
                } catch (_) {
                    // Ignora silenciosamente los errores
                }
            });
        });
    },

    // Método para inyectar el banner del partido en el DOM
    _injectPartyBanner(imgUrl, partidoName) {
        // Objetivo: colocar el logo dentro del apartado principal (contenido) centrado.
        const content = document.querySelector('.o_content');
        const controlPanel = document.querySelector('.o_control_panel');
        if (!content && !controlPanel) return;

        // Si ya existe el banner, muévelo al nuevo contenedor en vez de crear otro
        const existing = document.getElementById('pp_party_banner');
        if (existing) {
            if (content) {
                content.insertAdjacentElement('afterbegin', existing);
            }
            return;
        }

        // Crea el contenedor del banner alineado al centro
        const bar = document.createElement('div');
        bar.id = 'pp_party_banner';
        bar.className = 'pp-party-banner';
        bar.innerHTML = `
            <div class="pp-party-banner__inner">
                <img class="pp-party-banner__logo" src="${imgUrl}" alt="${partidoName}"/>
            </div>
        `;

        // Inserta el banner al inicio del área de contenido (preferido) o, como
        // respaldo, debajo de la barra de búsqueda como antes.
        if (content) {
            content.insertAdjacentElement('afterbegin', bar);
        } else if (controlPanel) {
            const bottom = controlPanel.querySelector('.o_cp_bottom');
            const top = controlPanel.querySelector('.o_cp_top');
            if (bottom) {
                bottom.insertAdjacentElement('afterend', bar);
            } else if (top) {
                top.insertAdjacentElement('afterend', bar);
            } else {
                controlPanel.appendChild(bar);
            }
        }
    },
});
