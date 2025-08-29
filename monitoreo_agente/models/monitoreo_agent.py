
from datetime import timedelta, date
from odoo import models, fields, api

class MonitoreoAgent(models.Model):
    _name = 'monitoreo.agent'
    _description = 'Agente Monitoreado'

    # --- Datos básicos del agente ---
    name = fields.Char("Nombre", required=True)
    state = fields.Selection([
        ('online', 'En línea'),
        ('offline', 'Desconectado'),
        ('error', 'Error'),
    ], string="Estado", default="offline")
    last_update = fields.Datetime("Última Actualización", default=fields.Datetime.now)

    # --- Relación con llamadas ---
    call_ids = fields.One2many('monitoreo.call', 'agent_id', string='Llamadas')
    call_ids_7d = fields.One2many(
        'monitoreo.call',
        string='Llamadas (7 días)',
        compute='_compute_call_ids_7d',
        readonly=True,
    )

    # --- Estadísticas de llamadas ---
    call_count_today = fields.Integer("Llamadas Hoy", compute="_compute_call_count_today")
    calls_total_7d = fields.Integer("Total Llamadas 7 días", compute="_compute_calls_per_day")

    # --- Llamadas por día (últimos 7 días) ---
    calls_day_1 = fields.Integer("Llamadas Día 1", compute="_compute_calls_per_day")  # Hoy
    calls_day_2 = fields.Integer("Llamadas Día 2", compute="_compute_calls_per_day")  # Ayer
    calls_day_3 = fields.Integer("Llamadas Día 3", compute="_compute_calls_per_day")
    calls_day_4 = fields.Integer("Llamadas Día 4", compute="_compute_calls_per_day")
    calls_day_5 = fields.Integer("Llamadas Día 5", compute="_compute_calls_per_day")
    calls_day_6 = fields.Integer("Llamadas Día 6", compute="_compute_calls_per_day")
    calls_day_7 = fields.Integer("Llamadas Día 7", compute="_compute_calls_per_day")

    # --- Porcentajes para gráfico de barras (visualización) ---
    calls_day_1_percent = fields.Integer("Porcentaje Día 1", compute="_compute_calls_per_day")
    calls_day_2_percent = fields.Integer("Porcentaje Día 2", compute="_compute_calls_per_day")
    calls_day_3_percent = fields.Integer("Porcentaje Día 3", compute="_compute_calls_per_day")
    calls_day_4_percent = fields.Integer("Porcentaje Día 4", compute="_compute_calls_per_day")
    calls_day_5_percent = fields.Integer("Porcentaje Día 5", compute="_compute_calls_per_day")
    calls_day_6_percent = fields.Integer("Porcentaje Día 6", compute="_compute_calls_per_day")
    calls_day_7_percent = fields.Integer("Porcentaje Día 7", compute="_compute_calls_per_day")

    # --- Métodos computados ---
    @api.depends('call_ids.start_datetime')
    def _compute_call_count_today(self):
        today = fields.Date.today()
        tomorrow = today + timedelta(days=1)
        for rec in self:
            rec.call_count_today = self.env['monitoreo.call'].search_count([
                ('agent_id', '=', rec.id),
                ('start_datetime', '>=', today),
                ('start_datetime', '<', tomorrow),
            ])

    @api.depends('call_ids.start_datetime')
    def _compute_calls_per_day(self):
        for rec in self:
            today = date.today()
            # Inicializar todos los contadores en 0
            rec.calls_day_1 = 0
            rec.calls_day_2 = 0
            rec.calls_day_3 = 0
            rec.calls_day_4 = 0
            rec.calls_day_5 = 0
            rec.calls_day_6 = 0
            rec.calls_day_7 = 0
            rec.calls_total_7d = 0

            if rec.id:
                total_calls = 0
                call_counts = []
                # Calcular para cada día (últimos 7 días)
                for i in range(7):
                    day_date = today - timedelta(days=i)
                    next_day = day_date + timedelta(days=1)
                    call_count = self.env['monitoreo.call'].search_count([
                        ('agent_id', '=', rec.id),
                        ('start_datetime', '>=', day_date),
                        ('start_datetime', '<', next_day),
                    ])
                    setattr(rec, f'calls_day_{i+1}', call_count)
                    call_counts.append(call_count)
                    total_calls += call_count
                rec.calls_total_7d = total_calls
                # Calcular porcentajes para barras horizontales
                max_calls = max(call_counts) if call_counts and max(call_counts) > 0 else 1
                for i, count in enumerate(call_counts):
                    percent = int((count / max_calls) * 100) if max_calls > 0 else 0
                    setattr(rec, f'calls_day_{i+1}_percent', percent)

    @api.depends('call_ids.start_datetime')
    def _compute_call_ids_7d(self):
        limit_from = fields.Datetime.now() - timedelta(days=7)
        Call = self.env['monitoreo.call']
        for rec in self:
            if rec.id:
                rec.call_ids_7d = Call.search([
                    ('agent_id', '=', rec.id),
                    ('start_datetime', '>=', limit_from),
                ], order='start_datetime desc')
            else:
                rec.call_ids_7d = Call.browse()

    # --- Acción para abrir gráfico de llamadas ---
    def action_view_calls_graph_7d(self):
        """Abrir gráfico de llamadas de los últimos 7 días para este agente"""
        limit_from = fields.Datetime.now() - timedelta(days=7)
        return {
            'type': 'ir.actions.act_window',
            'name': f'Gráfico de Llamadas - {self.name} (7 días)',
            'res_model': 'monitoreo.call',
            'view_mode': 'graph',
            'view_id': self.env.ref('monitoreo_agente.view_monitoreo_call_graph').id,
            'domain': [
                ('agent_id', '=', self.id),
                ('start_datetime', '>=', limit_from),
            ],
            'target': 'new',
            'context': {
                'graph_measure': 'duration',
                'graph_mode': 'line',
                'graph_groupbys': ['start_datetime:day'],
            }
        }
