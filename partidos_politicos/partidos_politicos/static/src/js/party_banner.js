/** @odoo-module */
import { ListController } from '@web/views/list/list_controller';
import { patch } from '@web/core/utils/patch';
import { onMounted } from '@odoo/owl';

/*
Purpose: For readonly users in politico.carga list view ("Mi Partido"), render a centered
party logo banner right below the search bar. The banner shows the logo of the party
assigned to the current user (politico.asignacion -> partido_id). If the user has no assignment,
no banner is shown.
*/

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

const _superSetup = ListController.prototype.setup;

patch(ListController.prototype, {
    setup() {
        _superSetup.call(this, ...arguments);
        // Only on politico.carga list view
        if (!(this.props && this.props.resModel === 'politico.carga')) return;

        this.orm = this.env.services.orm;
        const user = this.env.services.user;

        // Determine readonly (not admin)
        this._ppIsAdminPromise = Promise.resolve(false);
        try {
            if (user && user.hasGroup) {
                const r = user.hasGroup('base.group_system');
                this._ppIsAdminPromise = (r && typeof r.then === 'function') ? r : Promise.resolve(!!r);
            }
        } catch (_) {}

        onMounted(() => {
            (this._ppIsAdminPromise || Promise.resolve(false)).then(async (isAdmin) => {
                if (isAdmin) return; // Only readonly users should see the banner
                try {
                    // Find user's party via politico.asignacion
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

                    this._injectPartyBanner(imgUrl, partidoName);
                } catch (_) {
                    // silently ignore
                }
            });
        });
    },

    _injectPartyBanner(imgUrl, partidoName) {
        if (document.getElementById('pp_party_banner')) return;
        const controlPanel = document.querySelector('.o_control_panel');
        if (!controlPanel) return;

        // Create banner container aligned centered below search bar
        const bar = document.createElement('div');
        bar.id = 'pp_party_banner';
        bar.className = 'pp-party-banner';
        bar.innerHTML = `
            <div class="pp-party-banner__inner">
                <img class="pp-party-banner__logo" src="${imgUrl}" alt="${partidoName}"/>
            </div>
        `;

        // Insert after the main search bar row
        const bottom = controlPanel.querySelector('.o_cp_bottom');
        const top = controlPanel.querySelector('.o_cp_top');
        if (bottom) {
            bottom.insertAdjacentElement('afterend', bar);
        } else if (top) {
            top.insertAdjacentElement('afterend', bar);
        } else {
            controlPanel.appendChild(bar);
        }
    },
});
