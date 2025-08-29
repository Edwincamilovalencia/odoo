/** @odoo-module **/
/**
 * Barra de filtros personalizada para retain.call.history:
 * - Logo Odoo (izquierda)
 * - Selector de Agente(s) (dropdown con búsqueda y checkboxes)
 * - Rango de fechas (flatpickr; fallback nativo si no está disponible)
 * - Aplicación automática de filtros y persistencia en localStorage
 */

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

const _superSetup = ListController.prototype.setup;

patch(ListController.prototype, {
    /**
     * Inicializa la barra solo en el modelo retain.call.history.
     * Carga agentes, inyecta el DOM y restaura estado guardado.
     */
    setup() {
        _superSetup.call(this, ...arguments);
        const model = this.model && this.model.config && this.model.config.resModel;
        this._retainEnabled = model === "retain.call.history";
        if (this._retainEnabled) {
            this.orm = this.env.services.orm;
            this.retainAgents = [];
            this._retainDocClickBound = false;

            // Cargar lista única de agentes
            this._loadRetainAgents();

            // Asegurar DOM y widgets tras montar
            onMounted(() => {
                this._injectRetainHeaderIfMissing();
                this._initRangePicker();
                this._restoreUIFromStorage();
                // Si volvemos desde una vista de formulario con una búsqueda activa, pero sin filtros propios,
                // limpia la búsqueda nativa para evitar que quede "pegada".
                this._ensureSearchResetOnReturn();
                this._relocateDropdownNextToSearch();
            });
        }
    },

    /**
     * Reubica el dropdown nativo de Odoo (si existe) justo a la derecha de la búsqueda,
     * para evitar solaparse con nuestra barra.
     */
    _relocateDropdownNextToSearch() {
        try {
            const cp = document.querySelector('.o_control_panel .o_cp_bottom_left') || document.querySelector('.o_control_panel');
            const search = cp?.querySelector('.o_searchview');
            if (!cp || !search) return;
            if (cp.dataset.retainDropdownMoved === '1') return;

            const toggle = cp.querySelector('.dropdown-toggle, [data-bs-toggle="dropdown"], .o_dropdown_toggler');
            if (!toggle) return;

            const dropContainer = toggle.closest('.o_dropdown') || toggle;
            if (dropContainer && dropContainer !== search.nextSibling) {
                search.parentElement.insertBefore(dropContainer, search.nextSibling);
                cp.dataset.retainDropdownMoved = '1';
            }
        } catch (_) { /* silencioso */ }
    },

    /**
     * Lee agentes desde retain.call.history y deduplica por nombre.
     * Pinta el dropdown si ya existe.
     */
    async _loadRetainAgents() {
        try {
            const rows = await this.env.services.orm.searchRead("retain.call.history", [], ["agent_name"], { limit: 0 });
            const uniq = [...new Set(rows.map((r) => r.agent_name).filter(Boolean))].sort();
            this.retainAgents = uniq;

            this._populateAgentDropdown();
            this._updateAgentDropdownLabel();
        } catch (_) { /* silencioso */ }
    },

    /**
     * Inyecta la barra si aún no existe y enlaza eventos básicos.
     */
    _injectRetainHeaderIfMissing() {
        if (document.getElementById("retain_header_dom")) return;

        const bottomLeft = document.querySelector(".o_control_panel .o_cp_bottom_left");
        const cp = bottomLeft || document.querySelector(".o_control_panel");
        if (!cp) return;

    // Mostrar/ocultar chips nativos según si hay filtros propios activos
    this._toggleChipsVisibility();

        const wrapper = document.createElement("div");
        wrapper.id = "retain_header_dom";
        wrapper.className = "o_retain_bar";

        // Nota: estilos críticos del menú se duplican inline para evitar parpadeos si el SCSS
        // aún no está cargado por los assets.
        wrapper.innerHTML = `
            <div class="logo-col"><img class="logo" src="/retain_call_history/static/src/img/AiLumex_logo.png" alt="AiLumex"/></div>
            <div class="agents retain-dropdown-multiselect">
                <div id="retain_agent_dropdown" class="retain-dropdown">
                    <button class="btn btn-outline-secondary btn-sm retain-dd-btn" id="retainAgentDropdownBtn" type="button" aria-expanded="false" aria-label="Seleccionar agentes">
                        <span id="retainAgentDropdownLabel">Agente(s)</span>
                        <span class="caret" style="margin-left:6px;">▾</span>
                    </button>
                    <div class="retain-menu" id="retainAgentDropdownMenu" style="display:none; max-height: 260px; overflow:auto; min-width: 220px; background:#fff; border:1px solid #ddd; border-radius:6px; box-shadow:0 6px 18px rgba(0,0,0,.08); padding:6px 0; z-index: 1051; position:absolute;"></div>
                </div>
            </div>
            <div class="dates">
                <input id="retain_date_range" class="o_input" type="text" placeholder="dd/mm/aaaa a dd/mm/aaaa"/>
                <div id="retain_dates_fallback" class="d-none inline">
                    <input id="retain_date_from" class="o_input" type="date" placeholder="dd/mm/aaaa"/>
                    <span class="range-sep">a</span>
                    <input id="retain_date_to" class="o_input" type="date" placeholder="dd/mm/aaaa"/>
                </div>
            </div>
            <div class="actions">
                <button id="retain_clear_btn" class="btn btn-secondary btn-sm">Limpiar filtros</button>
            </div>`;

        // Insertar al final del bloque izquierdo del control panel
        (bottomLeft || cp).appendChild(wrapper);

        // Dropdown: construir, etiquetar y enlazar eventos
        this._populateAgentDropdown();
        this._updateAgentDropdownLabel();
        this._bindAgentDropdownEvents();

        // Botón: limpiar todo
        const clearBtn = wrapper.querySelector('#retain_clear_btn');
        clearBtn?.addEventListener('click', (ev) => { ev.preventDefault(); this.clearRetainFilters(); });

    // Fallback nativo: aplicar al cambiar fechas cuando no hay flatpickr
    const fdf = wrapper.querySelector('#retain_date_from');
    const fdt = wrapper.querySelector('#retain_date_to');
    const handleNativeChange = (ev) => { ev && ev.preventDefault && ev.preventDefault(); this.applyRetainFilters(); };
    fdf?.addEventListener('change', handleNativeChange);
    fdt?.addEventListener('change', handleNativeChange);
    },

    /**
     * Construye el menú de agentes con buscador y checkboxes.
     */
    _populateAgentDropdown() {
        const menu = document.getElementById("retainAgentDropdownMenu");
        if (!menu) return;

        menu.innerHTML = "";

        // Buscador local dentro del menú
        if (!menu.querySelector('.retain-search')) {
            const s = document.createElement('input');
            s.type = 'search';
            s.placeholder = 'Buscar agente...';
            s.className = 'retain-search';
            s.addEventListener('input', (ev) => {
                const q = (ev.target.value || '').toLowerCase().trim();
                menu.querySelectorAll('.dropdown-item').forEach(item => {
                    const txt = item.textContent.toLowerCase();
                    item.style.display = txt.indexOf(q) !== -1 ? '' : 'none';
                });
            });
            menu.appendChild(s);
        }

        // Posicionar el menú bajo el botón
        const btn = document.getElementById("retainAgentDropdownBtn");
        if (btn) {
            const parent = btn.closest('.retain-dropdown') || btn.parentElement;
            parent.style.position = "relative";
            menu.style.top = `${(btn.offsetHeight || 30) + 8}px`;
            menu.style.left = "0";
        }

        // Sin datos
        if (!this.retainAgents || !this.retainAgents.length) {
            const empty = document.createElement("div");
            empty.className = "dropdown-item-text text-muted";
            empty.style.padding = "6px 12px";
            empty.textContent = "Sin agentes";
            menu.appendChild(empty);
            return;
        }

        // Conservar selección previa
        const stored = this._getStoredAgents();

        // Pintar items
        this.retainAgents.forEach(agent => {
            const item = document.createElement("label");
            item.className = "dropdown-item";
            item.style.cssText = "align-items:center; gap:8px; padding:8px 12px; cursor:pointer;";
            item.innerHTML = `<input type="checkbox" class="retain-agent-checkbox" value="${agent}"/> <span>${agent}</span>`;
            const cb = item.querySelector('input[type="checkbox"]');
            if (stored.includes(agent)) cb.checked = true;
            menu.appendChild(item);
        });
    },

    /**
     * Enlaza abrir/cerrar del menú, aplicar filtros al cambiar y cierre al clicar fuera.
     */
    _bindAgentDropdownEvents() {
        const menu = document.getElementById("retainAgentDropdownMenu");
        const btn = document.getElementById("retainAgentDropdownBtn");
        if (!menu || !btn) return;

        btn.addEventListener("click", (e) => {
            e.preventDefault();
            const show = menu.style.display !== "block";
            menu.style.display = show ? "block" : "none";
            btn.setAttribute("aria-expanded", show ? "true" : "false");
        });

        // Aplicar al marcar/desmarcar
        menu.addEventListener("change", (ev) => {
            if (ev.target && ev.target.classList.contains("retain-agent-checkbox")) {
                this._updateAgentDropdownLabel();
                this.applyRetainFilters();
            }
        });

        // Evitar burbujeo interno
        menu.addEventListener("click", (e) => e.stopPropagation());
        btn.addEventListener("click", (e) => e.stopPropagation());

        // Cerrar al clicar fuera (se ata una sola vez)
        if (!this._retainDocClickBound) {
            document.addEventListener("click", () => {
                if (menu.style.display === "block") {
                    menu.style.display = "none";
                    btn.setAttribute("aria-expanded", "false");
                }
            });
            this._retainDocClickBound = true;
        }
    },

    /**
     * Actualiza la etiqueta del botón con el resumen de selección.
     */
    _updateAgentDropdownLabel() {
        const menu = document.getElementById("retainAgentDropdownMenu");
        const label = document.getElementById("retainAgentDropdownLabel");
        if (!menu || !label) return;

        const checked = Array.from(menu.querySelectorAll('input.retain-agent-checkbox:checked')).map(cb => cb.value);
        if (!checked.length) label.textContent = "Agente(s)";
        else if (checked.length === 1) label.textContent = checked[0];
        else label.textContent = `${checked.length} agentes`;
    },

    /** Devuelve agentes seleccionados actualmente. */
    _getSelectedAgentsFromDropdown() {
        const menu = document.getElementById("retainAgentDropdownMenu");
        if (!menu) return [];
        return Array.from(menu.querySelectorAll('input.retain-agent-checkbox:checked')).map(cb => cb.value);
    },

    /** Desmarca todas las casillas del menú. */
    _clearAgentDropdown() {
        const menu = document.getElementById("retainAgentDropdownMenu");
        if (!menu) return;
        menu.querySelectorAll('input.retain-agent-checkbox').forEach(cb => cb.checked = false);
        this._updateAgentDropdownLabel();
    },

    /** Lee selección guardada de localStorage (compat. legado). */
    _getStoredAgents() {
        let agentsStored = [];
        const multiJSON = window.localStorage.getItem('retain_agents');
        const singleLegacy = window.localStorage.getItem('retain_agent'); // compatibilidad
        if (multiJSON) {
            try { agentsStored = JSON.parse(multiJSON) || []; } catch (_) { agentsStored = []; }
        } else if (singleLegacy) {
            agentsStored = singleLegacy ? [singleLegacy] : [];
        }
        return agentsStored;
    },

    /**
     * Limpia agentes y fechas; reinicia búsqueda sin dominio.
     * También limpia el estado persistido en localStorage.
     */
    async clearRetainFilters() {
        // Agentes
        this._clearAgentDropdown();

        // Fechas
        const rangeInput = document.getElementById('retain_date_range');
        if (this._fp) {
            this._fp.clear();
            if (rangeInput) rangeInput.value = "";
        } else if (rangeInput) {
            rangeInput.value = "";
            const fdf = document.getElementById('retain_date_from');
            const fdt = document.getElementById('retain_date_to');
            if (fdf) fdf.value = "";
            if (fdt) fdt.value = "";
        }

        // Storage
        window.localStorage.removeItem('retain_agent');
        window.localStorage.removeItem('retain_agents');
        window.localStorage.removeItem('retain_date_from');
        window.localStorage.removeItem('retain_date_to');

        // Reiniciar resultados usando el SearchModel
        const sm = this.env.searchModel;
        if (sm && typeof sm.clearQuery === "function" && typeof sm.reload === "function") {
            try {
                sm.clearQuery();
                await sm.reload({ domain: [] });
                return;
            } catch (e) { /* fallback abajo */ }
        }

        // Fallback: reabrir acción sin filtros
        const mergedCtx = {
            retain_agents: [],
            retain_date_from: false,
            retain_date_to: false,
            search_default_retain_agents_filter: 0,
            search_default_retain_date_from_filter: 0,
            search_default_retain_date_to_filter: 0,
        };
        this.env.services.action.doAction("retain_call_history.action_retain_call_history", {
            additionalContext: mergedCtx,
            replaceLastAction: true,
            clearBreadcrumbs: true,
        });
    },

    /**
     * Inicializa flatpickr en modo rango. Si no existe, muestra fallback nativo.
     */
    _initRangePicker() {
        const input = document.getElementById("retain_date_range");
        if (!input) return;

        if (window.flatpickr) {
            this._fp = window.flatpickr(input, {
                mode: "range",
                // Mostrar dd/mm/aaaa pero mantener valor real en Y-m-d
                dateFormat: "Y-m-d",
                altInput: true,
                altFormat: "d/m/Y",
                locale: {
                    firstDayOfWeek: 1,
                    weekdays: {
                        shorthand: ["Do","Lu","Ma","Mi","Ju","Vi","Sa"],
                        longhand: ["Domingo","Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"],
                    },
                    months: {
                        shorthand: ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"],
                        longhand: ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"],
                    },
                    rangeSeparator: " a ",
                },
                showMonths: 2,
                // Evitar entradas manuales ambiguas (mejor para usuarios solo lectura)
                allowInput: false,
                onChange: () => this._maybeAutoApplyRange(),
                onClose: () => this._maybeAutoApplyRange(),
            });
        } else {
            // Fallback: mostrar inputs nativos y ocultar el de rango
            const fb = document.getElementById('retain_dates_fallback');
            if (fb) fb.classList.remove('d-none');
            if (input) input.classList.add('d-none');
        }
    },

    /**
     * Restaura selección de agentes/fechas desde localStorage hacia la UI.
     */
    _restoreUIFromStorage() {
        // Agentes
        const stored = this._getStoredAgents();
        const menu = document.getElementById("retainAgentDropdownMenu");
        if (menu) {
            if (!menu.children.length) this._populateAgentDropdown();
            menu.querySelectorAll('input.retain-agent-checkbox').forEach(cb => {
                cb.checked = stored.includes(cb.value);
            });
            this._updateAgentDropdownLabel();
        }

        // Fechas
        const df = window.localStorage.getItem('retain_date_from') || '';
        const dt = window.localStorage.getItem('retain_date_to') || '';
        if (this._fp && (df || dt)) {
            try {
                const dates = [];
                if (df) dates.push(new Date(df));
                if (dt) dates.push(new Date(dt));
                if (dates.length) this._fp.setDate(dates, true);
            } catch (e) { /* silencioso */ }
        } else {
            const fdf = document.getElementById('retain_date_from');
            const fdt = document.getElementById('retain_date_to');
            if (fdf) fdf.value = df;
            if (fdt) fdt.value = dt;
        }

    // Ajustar visibilidad de chips según el estado restaurado
    this._toggleChipsVisibility();
    },

    /** Aplica filtros cuando cambia el rango (flatpickr). */
    _maybeAutoApplyRange() {
        if (!this._fp) return;
        this.applyRetainFilters();
    },

    /**
     * Lee estado de la UI (agentes + fechas) normalizado.
     * Invierte fechas si el usuario las ingresó al revés.
     */
    _retainReadUI() {
        // Agentes
        const agents = this._getSelectedAgentsFromDropdown();

        // Fechas
        let dateFrom = "";
        let dateTo = "";
        if (this._fp && this._fp.selectedDates && this._fp.selectedDates.length) {
            const [d0, d1] = this._fp.selectedDates;
            if (d0) dateFrom = this._formatDateLocal(d0);
            if (d1) dateTo = this._formatDateLocal(d1);
        } else {
            const df = document.getElementById('retain_date_from');
            const dt = document.getElementById('retain_date_to');
            if (df?.value) dateFrom = df.value;
            if (dt?.value) dateTo = dt.value;
        }

        // Si selecciona solo un día, interpretarlo como rango de 1 día
        if (dateFrom && !dateTo) {
            dateTo = dateFrom;
        }

        // Normalizar orden si viene invertido
        if (dateFrom && dateTo && dateFrom > dateTo) {
            const tmp = dateFrom; dateFrom = dateTo; dateTo = tmp;
            if (this._fp) {
                try {
                    const d1 = new Date(dateFrom);
                    const d2 = new Date(dateTo);
                    this._fp.setDate([d1, d2], true);
                } catch (_) { /* silencioso */ }
            } else {
                const df = document.getElementById('retain_date_from');
                const dt = document.getElementById('retain_date_to');
                if (df) df.value = dateFrom;
                if (dt) dt.value = dateTo;
            }
        }
        return { agents, dateFrom, dateTo };
    },

    /** Convierte Date a YYYY-MM-DD en hora local (evita desfase por UTC). */
    _formatDateLocal(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    },

    /**
     * Aplica el dominio al SearchModel y persiste selección en localStorage.
     * Fallback: reabre la acción con contexto por defecto.
     */
    async applyRetainFilters() {
        const { agents, dateFrom, dateTo } = this._retainReadUI();

        const domain = [];
        if (agents.length) domain.push(["agent_name", "in", agents]);
        if (dateFrom) domain.push(["call_date", ">=", `${dateFrom} 00:00:00`]);
        if (dateTo) domain.push(["call_date", "<=", `${dateTo} 23:59:59`]);

    const sm = this.env.searchModel;
    if (sm && typeof sm.reload === "function") {
        try {
            if (typeof sm.clearQuery === 'function') {
                await sm.clearQuery();
            }
            await sm.reload({ domain });

            // Persistir estado
            window.localStorage.removeItem('retain_agent'); // legacy
            window.localStorage.setItem('retain_agents', JSON.stringify(agents));
            window.localStorage.setItem('retain_date_from', dateFrom || '');
            window.localStorage.setItem('retain_date_to', dateTo || '');

            // Actualizar visibilidad de chips nativos
            this._toggleChipsVisibility();
            return;
        } catch (e) { /* fallback abajo */ }
        }

        // Fallback: acción con contexto
        const ctx = {};
        if (agents.length) {
            ctx.retain_agents = agents;
            ctx.search_default_retain_agents_filter = 1;
        } else {
            ctx.retain_agents = [];
            ctx.search_default_retain_agents_filter = 0;
        }
        if (dateFrom) {
            ctx.retain_date_from = `${dateFrom} 00:00:00`;
            ctx.search_default_retain_date_from_filter = 1;
        } else {
            ctx.retain_date_from = false;
            ctx.search_default_retain_date_from_filter = 0;
        }
        if (dateTo) {
            ctx.retain_date_to = `${dateTo} 23:59:59`;
            ctx.search_default_retain_date_to_filter = 1;
        } else {
            ctx.retain_date_to = false;
            ctx.search_default_retain_date_to_filter = 0;
        }

        // Persistencia UI
        window.localStorage.removeItem('retain_agent');
        window.localStorage.setItem('retain_agents', JSON.stringify(agents));
        window.localStorage.setItem('retain_date_from', dateFrom || '');
        window.localStorage.setItem('retain_date_to', dateTo || '');

        this.env.services.action.doAction("retain_call_history.action_retain_call_history", {
            additionalContext: ctx,
            replaceLastAction: true,
            clearBreadcrumbs: true,
        });
    },

    /** Muestra u oculta chips nativos de búsqueda segun si hay filtros propios activos. */
    _toggleChipsVisibility() {
        try {
            const cp = document.querySelector('.o_control_panel');
            if (!cp) return;
            const storedAgents = this._getStoredAgents();
            const df = window.localStorage.getItem('retain_date_from') || '';
            const dt = window.localStorage.getItem('retain_date_to') || '';
            const hasOwnStored = (storedAgents && storedAgents.length) || df || dt;
            const hasCurrentRange = !!(this._fp && this._fp.selectedDates && this._fp.selectedDates.length);
            if (hasOwnStored || hasCurrentRange) cp.classList.add('retain-hide-chips');
            else cp.classList.remove('retain-hide-chips');
        } catch (_) { /* silencioso */ }
    },

    /**
     * Si volvemos del formulario y no hay filtros propios guardados, pero hay búsqueda activa,
     * limpia la búsqueda para que el listado no quede "atrapado" en un query previo.
     */
    _ensureSearchResetOnReturn() {
        try {
            // Evitar limpiar repetidamente en el mismo render
            const cp = document.querySelector('.o_control_panel');
            if (!cp || cp.dataset.retainSearchChecked === '1') return;
            cp.dataset.retainSearchChecked = '1';

            const storedAgents = this._getStoredAgents();
            const df = window.localStorage.getItem('retain_date_from') || '';
            const dt = window.localStorage.getItem('retain_date_to') || '';
            const hasOwn = (storedAgents && storedAgents.length) || df || dt;

            const hasFacets = !!document.querySelector('.o_searchview .o_searchview_facet');
            const input = document.querySelector('.o_searchview input.o_searchview_input');
            const hasText = !!(input && input.value && input.value.trim().length);

            // Modo no intrusivo para usuarios de solo lectura: no toques búsqueda nativa.
            // Solo dejamos la barra en estado consistente con nuestros filtros.
            // Si en el futuro se desea limpiar automáticamente, hacerlo bajo una preferencia.
        } catch (_) { /* silencioso */ }
    },

    /** Limpia UI nativa de búsqueda (input y chips/facets), sin tocar nuestros filtros. */
    _clearNativeSearchUI() {
        try {
            const input = document.querySelector('.o_searchview input.o_searchview_input');
            if (input) {
                input.value = '';
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }
            document.querySelectorAll('.o_searchview .o_facet_remove').forEach(btn => btn.click());
        } catch (_) { /* silencioso */ }
    },
});
