
/** @odoo-module */
import { ListController } from '@web/views/list/list_controller';
import { patch } from '@web/core/utils/patch';
import { onMounted } from '@odoo/owl';

// --- Funciones auxiliares deben estar fuera del patch para el correcto binding ---
// Carga los partidos seleccionados almacenados en sessionStorage (multi o legacy single)
function _loadStoredPartidos() {
    // Lee primero el formato múltiple, si no existe usa el formato antiguo de uno solo
    const multi = sessionStorage.getItem('pp_partido_filter_multi');
    if (multi) {
        try { const arr = JSON.parse(multi) || []; return arr.map(Number).filter(Boolean); } catch (_) { /* ignorar */ }
    }
    const single = sessionStorage.getItem('pp_partido_filter');
    if (single) {
        const id = parseInt(single);
        return isNaN(id) ? [] : [id];
    }
    return [];
}

 // Asegura que el filtro de partidos esté listo y visible en el DOM
async function _ensureFilterReady() {
    await (this._ppLoadPromise || Promise.resolve());
    if (document.getElementById('pp_partido_filter_dropdown')) return;
    const cp = document.querySelector('.o_control_panel .o_cp_bottom_left') || document.querySelector('.o_control_panel');
    if (!cp) {
        requestAnimationFrame(() => this._ensureFilterReady());
        return;
    }
    this._injectPartidoDropdown(cp);
    // Aplica el dominio persistido solo una vez al primer render
    const sel = this._ppSelected || [];
    if (!this._ppDomainApplied) {
        let domain = [];
        if (sel.length) domain = [['partido_id', 'in', sel]];
        if (this.env.searchModel && typeof this.env.searchModel.clearQuery === 'function') {
            await this.env.searchModel.clearQuery();
        }
        this.env.searchModel.reload({ domain });
        this._ppDomainApplied = true;
    }
}

// Devuelve la etiqueta del dropdown según la selección actual
function _getDropdownLabel() {
    const sel = this._ppSelected || [];
    if (!sel.length) return 'Partido(s)';
    if (sel.length === 1) {
        const partido = this._ppPartidos.find(p => Number(p.id) === Number(sel[0]));
        return partido ? partido.name : 'Partido(s)';
    }
    return `${sel.length} partidos`;
}

// Aplica la selección de partidos, actualiza el filtro y la etiqueta
async function _applyPartidosSelection(ids, btn, menu, closeMenu = false) {
    this._ppSelected = (ids || []).map(Number).filter(Boolean);
    sessionStorage.setItem('pp_partido_filter_multi', JSON.stringify(this._ppSelected));
    // Actualiza la etiqueta
    const label = btn.querySelector('#pp_partido_dropdown_label');
    if (label) label.textContent = this._getDropdownLabel();
    // Aplica el filtro: limpia el dominio anterior y recarga con el nuevo
    let domain = [];
    if (this._ppSelected.length) domain = [['partido_id', 'in', this._ppSelected]];
    if (this.env.searchModel && typeof this.env.searchModel.clearQuery === 'function') {
        await this.env.searchModel.clearQuery();
    }
    this.env.searchModel.reload({ domain });
    // Oculta el menú si se solicita
    if (closeMenu && menu) {
        menu.classList.remove('pp-dropdown-open');
        setTimeout(() => { menu.style.display = 'none'; }, 120);
    }
}

// Guarda la referencia al método original setup del ListController
const _superSetup = ListController.prototype.setup;

patch(ListController.prototype, {
    setup() {
        _superSetup.call(this, ...arguments);
        // Solo inicializa en politico.carga; luego verifica grupo admin y ejecuta en mount
        if (!(this.props && this.props.resModel === 'politico.carga')) return;
        this._ppEnabled = false;
        this.orm = this.env.services.orm;
        const user = this.env.services.user;
        try {
            if (user && user.hasGroup) {
                const r = user.hasGroup('base.group_system');
                this._ppIsAdminPromise = (r && typeof r.then === 'function') ? r : Promise.resolve(!!r);
            } else {
                this._ppIsAdminPromise = Promise.resolve(false);
            }
        } catch (_) {
            this._ppIsAdminPromise = Promise.resolve(false);
        }

        // Cuando el componente está montado, verifica si debe mostrar el filtro
        onMounted(() => {
            (this._ppIsAdminPromise || Promise.resolve(false)).then((isAdmin) => {
                if (!isAdmin) return; // usuarios solo lectura: no hacer nada
                this._ppEnabled = true;
                this._ppPartidos = [];
                this._ppSelected = _loadStoredPartidos();
                this._ppDomainApplied = false;
                this._ppLoadPromise = this._loadPartidos();
                // Asocia helpers a esta instancia
                this._ensureFilterReady = _ensureFilterReady.bind(this);
                this._getDropdownLabel = _getDropdownLabel.bind(this);
                this._applyPartidosSelection = _applyPartidosSelection.bind(this);
                this._ensureFilterReady();
            });
        });
    },

    // Carga la lista de partidos desde el backend
    async _loadPartidos() {
        try {
            const rows = await this.orm.searchRead('politico.partido', [], ['id', 'name'], { limit: 0 });
            this._ppPartidos = rows;
        } catch (_) {
            this._ppPartidos = [];
        }
    },

    // Inyecta el dropdown de filtro de partidos en el panel de control
    _injectPartidoDropdown(cp) {
        if (document.getElementById('pp_partido_filter_dropdown')) return;
        // Wrapper para alinear a la derecha
        const wrapper = document.createElement('div');
        wrapper.id = 'pp_partido_filter_dropdown';
        wrapper.className = 'pp-partido-dropdown-bar pp-dropdown-right';

        // Botón del dropdown
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'pp-dropdown-btn';
        btn.innerHTML = `<span id="pp_partido_dropdown_label">${this._getDropdownLabel()}</span> <span class="caret">▾</span>`;
        btn.style.position = 'relative';
        btn.style.zIndex = 2;

        // Menú desplegable
        const menu = document.createElement('div');
        menu.className = 'pp-dropdown-menu';
        menu.style.display = 'none';

        // Caja de búsqueda dentro del menú
        const s = document.createElement('input');
        s.type = 'search';
        s.placeholder = 'Buscar partido politico...';
        s.className = 'pp-search';
        s.addEventListener('input', (ev) => {
            const q = (ev.target.value || '').toLowerCase().trim();
            menu.querySelectorAll('.pp-dropdown-item.choice').forEach(item => {
                const txt = item.textContent.toLowerCase();
                item.style.display = txt.indexOf(q) !== -1 ? '' : 'none';
            });
        });
        menu.appendChild(s);

        // Opción: Todos (limpia selección)
        const todos = document.createElement('div');
        todos.className = 'pp-dropdown-item pp-item-action';
        todos.innerHTML = `<span>Todos</span>`;
        todos.onclick = () => this._applyPartidosSelection([], btn, menu, true);
        menu.appendChild(todos);

        // Opciones: partidos (checkboxes)
        this._ppPartidos.forEach(p => {
            const item = document.createElement('label');
            item.className = 'pp-dropdown-item choice';
            item.innerHTML = `<input type="checkbox" class="pp-partido-checkbox" value="${p.id}" ${this._ppSelected.includes(Number(p.id)) ? 'checked' : ''}/> <span>${p.name}</span>`;
            menu.appendChild(item);
        });

        // Aplica al cambiar cualquier checkbox
        menu.addEventListener('change', (ev) => {
            if (ev.target && ev.target.classList.contains('pp-partido-checkbox')) {
                const selected = Array.from(menu.querySelectorAll('.pp-partido-checkbox:checked')).map(cb => Number(cb.value));
                this._applyPartidosSelection(selected, btn, menu, false);
            }
        });

        // Botón para limpiar filtros
        const clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'pp-clear-btn';
        clearBtn.innerHTML = '<span class="pp-clear-x">&#10005;</span> Limpiar filtros';
        clearBtn.onclick = (ev) => {
            ev.preventDefault();
            this._applyPartidosSelection([], btn, menu, false); // reinicia a todos, pero no cierra menú
            // Visual: cerrar menú si abierto
            menu.classList.remove('pp-dropdown-open');
            setTimeout(() => { menu.style.display = 'none'; }, 120);
        };

        // Lógica para mostrar/ocultar el menú con animación
        btn.onclick = (ev) => {
            ev.preventDefault();
            if (menu.style.display === 'block') {
                menu.classList.remove('pp-dropdown-open');
                setTimeout(() => { menu.style.display = 'none'; }, 120);
            } else {
                menu.style.display = 'block';
                setTimeout(() => { menu.classList.add('pp-dropdown-open'); }, 10);
            }
        };
        // Oculta el menú al hacer click fuera (guarda handler para cleanup)
        this._ppDocClickHandler = (ev) => {
            if (!wrapper.contains(ev.target)) {
                menu.classList.remove('pp-dropdown-open');
                setTimeout(() => { menu.style.display = 'none'; }, 120);
            }
        };
        document.addEventListener('click', this._ppDocClickHandler);

        // Layout: dropdown + botón limpiar
        const innerBar = document.createElement('div');
        innerBar.className = 'pp-dropdown-innerbar';
        innerBar.appendChild(btn);
        innerBar.appendChild(clearBtn);
        wrapper.appendChild(innerBar);
        wrapper.appendChild(menu);

        // Inserta a la derecha del control panel
        const cpRight = cp.querySelector('.o_cp_bottom_right') || cp;
        cpRight.appendChild(wrapper);

        // handlers ya están adjuntos arriba
    },

    // Devuelve la etiqueta del dropdown según la selección actual
    _getDropdownLabel() {
        const sel = this._ppSelected || [];
        if (!sel.length) return 'Partido(s)';
        if (sel.length === 1) {
            const partido = this._ppPartidos.find(p => Number(p.id) === Number(sel[0]));
            return partido ? partido.name : 'Partido(s)';
        }
        return `${sel.length} partidos`;
    },

    // Limpia el filtro y los handlers al desmontar el componente
    onWillUnmount() {
        const old = document.getElementById('pp_partido_filter_dropdown');
        if (old) old.remove();
        if (this._ppDocClickHandler) {
            document.removeEventListener('click', this._ppDocClickHandler);
            this._ppDocClickHandler = null;
        }
        if (this._super) this._super(...arguments);
    },
});
