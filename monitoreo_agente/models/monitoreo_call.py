# -*- coding: utf-8 -*-
"""
Modelo: monitoreo.call
Registra llamadas monitoreadas.
"""
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta

class MonitoreoCall(models.Model):
    _name = 'monitoreo.call'
    _description = 'Llamada Monitoreada'
    _order = 'start_datetime desc'
    _sql_constraints = [
        ('duration_non_negative', 'CHECK(duration >= 0)', 'La duración debe ser no negativa.'),
    ]

    start_datetime = fields.Datetime(string='Fecha/Hora de Inicio', required=True, default=fields.Datetime.now)
    duration = fields.Float(string='Duración (minutos)')
    end_datetime = fields.Datetime(string='Fecha/Hora de Fin', compute='_compute_end_datetime', store=True)
    state = fields.Selection([
        ('success', 'Exitosa'),
        ('failed', 'Fallida'),
        ('dropped', 'Cortada'),
    ], string='Estado de la llamada', default='success', required=True)
    agent_id = fields.Many2one('monitoreo.agent', string='Agente Responsable', required=True)
    number_from = fields.Char(string='Número de Origen')
    number_to = fields.Char(string='Número de Destino')
    # Campo para mostrar otras llamadas del mismo agente
    related_calls_ids = fields.One2many('monitoreo.call', compute='_compute_related_calls', string='Llamadas Relacionadas')

    @api.depends('start_datetime', 'duration')
    def _compute_end_datetime(self):
        for record in self:
            if record.start_datetime and record.duration:
                record.end_datetime = record.start_datetime + timedelta(minutes=record.duration)
            else:
                record.end_datetime = record.start_datetime

    def _compute_related_calls(self):
        for record in self:
            if record.agent_id:
                # Buscar llamadas del mismo agente en los últimos 7 días
                domain = [
                    ('agent_id', '=', record.agent_id.id),
                    ('start_datetime', '>=', fields.Datetime.now() - timedelta(days=7))
                ]
                related_calls = self.env['monitoreo.call'].search(domain, limit=10, order='start_datetime desc')
                record.related_calls_ids = related_calls.ids
            else:
                record.related_calls_ids = []

    def open_timeline_graph(self):
        self.ensure_one()
        if not self.id:
            return False
        action = self.env.ref('monitoreo_agente.action_monitoreo_call_timeline').read()[0]
        # Forzar el filtro por agente actual
        action['domain'] = [('agent_id', '=', self.agent_id.id)]
        action['context'] = {'default_agent_id': self.agent_id.id}
        return action

    @api.onchange('state')
    def _onchange_state_reset_duration(self):
        # Si una llamada es fallida, la duración debe ser 0
        for rec in self:
            if rec.state == 'failed':
                rec.duration = 0.0

    @api.constrains('state', 'duration')
    def _check_duration_for_failed(self):
        for rec in self:
            if rec.state == 'failed' and rec.duration:
                raise ValidationError(_('Una llamada fallida debe tener duración 0.'))
