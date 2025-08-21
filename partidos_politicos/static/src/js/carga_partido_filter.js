
/** @odoo-module */
import { ListController } from '@web/views/list/list_controller';
import { patch } from '@web/core/utils/patch';
import { onMounted } from '@odoo/owl';

// --- Helper functions must be outside the patch for correct binding ---
function _loadStoredPartidos() {
    // Read multi first, fallback to legacy single
    const multi = sessionStorage.getItem('pp_partido_filter_multi');
    if (multi) {
        try { const arr = JSON.parse(multi) || []; return arr.map(Number).filter(Boolean); } catch (_) { /* ignore */ }
    }
    const single = sessionStorage.getItem('pp_partido_filter');
    if (single) {
        const id = parseInt(single);
        return isNaN(id) ? [] : [id];
    }
    return [];
}

async function _ensureFilterReady() {
    await (this._ppLoadPromise || Promise.resolve());
    if (document.getElementById('pp_partido_filter_dropdown')) return;
    const cp = document.querySelector('.o_control_panel .o_cp_bottom_left') || document.querySelector('.o_control_panel');
    if (!cp) {
        requestAnimationFrame(() => this._ensureFilterReady());
        return;
    }
    this._injectPartidoDropdown(cp);
    // Apply persisted domain once on first render
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

function _getDropdownLabel() {
    const sel = this._ppSelected || [];
    if (!sel.length) return 'Partido(s)';
    if (sel.length === 1) {
        const partido = this._ppPartidos.find(p => Number(p.id) === Number(sel[0]));
        return partido ? partido.name : 'Partido(s)';
    }
    return `${sel.length} partidos`;
}

async function _applyPartidosSelection(ids, btn, menu, closeMenu = false) {
    this._ppSelected = (ids || []).map(Number).filter(Boolean);
    sessionStorage.setItem('pp_partido_filter_multi', JSON.stringify(this._ppSelected));
    // Update label
    const label = btn.querySelector('#pp_partido_dropdown_label');
    if (label) label.textContent = this._getDropdownLabel();
    // Apply filter: clear previous domain, then reload with new domain
    let domain = [];
    if (this._ppSelected.length) domain = [['partido_id', 'in', this._ppSelected]];
    if (this.env.searchModel && typeof this.env.searchModel.clearQuery === 'function') {
        await this.env.searchModel.clearQuery();
    }
    this.env.searchModel.reload({ domain });
    // Hide menu if requested
    if (closeMenu && menu) {
        menu.classList.remove('pp-dropdown-open');
        setTimeout(() => { menu.style.display = 'none'; }, 120);
    }
}

const _superSetup = ListController.prototype.setup;

patch(ListController.prototype, {
    setup() {
        _superSetup.call(this, ...arguments);
    // Only init on politico.carga; then check admin group via promise and run on mount
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

    onMounted(() => {
        (this._ppIsAdminPromise || Promise.resolve(false)).then((isAdmin) => {
            if (!isAdmin) return; // readonly users: do nothing
            this._ppEnabled = true;
            this._ppPartidos = [];
            this._ppSelected = _loadStoredPartidos();
            this._ppDomainApplied = false;
            this._ppLoadPromise = this._loadPartidos();
            // Bind helpers to this instance
            this._ensureFilterReady = _ensureFilterReady.bind(this);
            this._getDropdownLabel = _getDropdownLabel.bind(this);
            this._applyPartidosSelection = _applyPartidosSelection.bind(this);
            this._ensureFilterReady();
        });
    });
    },

    async _loadPartidos() {
        try {
            const rows = await this.orm.searchRead('politico.partido', [], ['id', 'name'], { limit: 0 });
            this._ppPartidos = rows;
        } catch (_) {
            this._ppPartidos = [];
        }
    },


    _injectPartidoDropdown(cp) {
        if (document.getElementById('pp_partido_filter_dropdown')) return;
        // Wrapper for centering below search
        const wrapper = document.createElement('div');
        wrapper.id = 'pp_partido_filter_dropdown';
        wrapper.className = 'pp-partido-dropdown-bar pp-dropdown-below-search';

        // Dropdown button
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'pp-dropdown-btn';
        btn.innerHTML = `<span id="pp_partido_dropdown_label">${this._getDropdownLabel()}</span> <span class="caret">▾</span>`;
        btn.style.position = 'relative';
        btn.style.zIndex = 2;

        // Dropdown menu
        const menu = document.createElement('div');
        menu.className = 'pp-dropdown-menu';
        menu.style.display = 'none';

        // Search box inside menu
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

        // Option: Todos (clear)
        const todos = document.createElement('div');
        todos.className = 'pp-dropdown-item pp-item-action';
        todos.innerHTML = `<span>Todos</span>`;
        todos.onclick = () => this._applyPartidosSelection([], btn, menu, true);
        menu.appendChild(todos);

        // Options: partidos (checkboxes)
        this._ppPartidos.forEach(p => {
            const item = document.createElement('label');
            item.className = 'pp-dropdown-item choice';
            item.innerHTML = `<input type="checkbox" class="pp-partido-checkbox" value="${p.id}" ${this._ppSelected.includes(Number(p.id)) ? 'checked' : ''}/> <span>${p.name}</span>`;
            menu.appendChild(item);
        });

        // Apply on change of any checkbox
        menu.addEventListener('change', (ev) => {
            if (ev.target && ev.target.classList.contains('pp-partido-checkbox')) {
                const selected = Array.from(menu.querySelectorAll('.pp-partido-checkbox:checked')).map(cb => Number(cb.value));
                this._applyPartidosSelection(selected, btn, menu, false);
            }
        });

        // Limpiar filtros button
        const clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'pp-clear-btn';
        clearBtn.innerHTML = '<span class="pp-clear-x">&#10005;</span> Limpiar filtros';
        clearBtn.onclick = (ev) => {
            ev.preventDefault();
            this._applyPartidosSelection([], btn, menu, false); // reset to all, but don't close menu
            // Visual: cerrar menú si abierto
            menu.classList.remove('pp-dropdown-open');
            setTimeout(() => { menu.style.display = 'none'; }, 120);
        };

        // Show/hide logic with animation
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
        // Hide on click outside (store handler for cleanup)
        this._ppDocClickHandler = (ev) => {
            if (!wrapper.contains(ev.target)) {
                menu.classList.remove('pp-dropdown-open');
                setTimeout(() => { menu.style.display = 'none'; }, 120);
            }
        };
        document.addEventListener('click', this._ppDocClickHandler);


    // Layout: dropdown + clear button
    const innerBar = document.createElement('div');
    innerBar.className = 'pp-dropdown-innerbar';
    innerBar.appendChild(btn);
    innerBar.appendChild(clearBtn);
    wrapper.appendChild(innerBar);
    wrapper.appendChild(menu);

        // Insert below search bar, centered
        const search = cp.querySelector('.o_searchview');
        if (search && search.parentElement) {
            // Create a full-width row below search
            let belowRow = cp.querySelector('.pp-dropdown-below-row');
            if (!belowRow) {
                belowRow = document.createElement('div');
                belowRow.className = 'pp-dropdown-below-row';
                belowRow.style.width = '100%';
                belowRow.style.display = 'flex';
                belowRow.style.justifyContent = 'center';
                belowRow.style.marginTop = '0.5em';
                search.parentElement.appendChild(belowRow);
            }
            belowRow.appendChild(wrapper);
        } else {
            cp.appendChild(wrapper);
        }

    // handlers already attached above
    },

    _getDropdownLabel() {
        const sel = this._ppSelected || [];
        if (!sel.length) return 'Partido(s)';
        if (sel.length === 1) {
            const partido = this._ppPartidos.find(p => Number(p.id) === Number(sel[0]));
            return partido ? partido.name : 'Partido(s)';
        }
        return `${sel.length} partidos`;
    },

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
// SCSS: ver static/src/scss/carga_partido_filter.scss
