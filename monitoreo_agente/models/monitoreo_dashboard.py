# -*- coding: utf-8 -*-
"""
Modelo: monitoreo.dashboard
Para mostrar tarjetas de dashboard en vista kanban
"""
from odoo import models, fields, api
from datetime import datetime, timedelta

class MonitoreoDashboard(models.Model):
    _name = 'monitoreo.dashboard'
    _description = 'Dashboard de Monitoreo'
    _rec_name = 'name'

    name = fields.Char(string='Nombre', required=True)
    dashboard_type = fields.Selection([
        ('calls_by_day', 'Llamadas por día'),
        ('agent_states', 'Estados de agentes'),
        ('calls_by_hour', 'Llamadas por hora'),
        ('recent_alerts', 'Alertas recientes'),
    ], string='Tipo de Dashboard', required=True)
    
    icon = fields.Char(string='Icono', default='fa-chart-bar')
    color = fields.Char(string='Color', default='primary')
    description = fields.Char(string='Descripción')
    count = fields.Integer(string='Contador', compute='_compute_count')
    
    @api.depends('dashboard_type')
    def _compute_count(self):
        for record in self:
            if record.dashboard_type == 'calls_by_day':
                # Llamadas de hoy
                today = fields.Date.today()
                tomorrow = today + timedelta(days=1)
                record.count = self.env['monitoreo.call'].search_count([
                    ('start_datetime', '>=', today),
                    ('start_datetime', '<', tomorrow)
                ])
            elif record.dashboard_type == 'agent_states':
                # Total de agentes activos
                record.count = self.env['monitoreo.agent'].search_count([
                    ('state', '=', 'online')
                ])
            elif record.dashboard_type == 'calls_by_hour':
                # Llamadas de la última hora
                one_hour_ago = fields.Datetime.now() - timedelta(hours=1)
                record.count = self.env['monitoreo.call'].search_count([
                    ('start_datetime', '>=', one_hour_ago)
                ])
            elif record.dashboard_type == 'recent_alerts':
                # Alertas de las últimas 24 horas
                yesterday = fields.Datetime.now() - timedelta(days=1)
                record.count = self.env['monitoreo.alert'].search_count([
                    ('create_date', '>=', yesterday)
                ])
            else:
                record.count = 0

    def action_open_dashboard(self):
        """Abrir el dashboard correspondiente"""
        self.ensure_one()
        if self.dashboard_type == 'calls_by_day':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Número (llamadas) por día',
                'res_model': 'monitoreo.call',
                'view_mode': 'graph',
                'target': 'new',
                'context': {
                    'graph_groupbys': ['start_datetime:day'],
                    'graph_measures': ['__count__'],
                    'graph_type': 'bar'
                }
            }
        elif self.dashboard_type == 'agent_states':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Estados de agentes',
                'res_model': 'monitoreo.agent',
                'view_mode': 'graph',
                'target': 'new',
                'context': {
                    'graph_groupbys': ['state'],
                    'graph_measures': ['__count__'],
                    'graph_type': 'pie'
                }
            }
        elif self.dashboard_type == 'calls_by_hour':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Número (llamadas) por hora (hoy)',
                'res_model': 'monitoreo.call',
                'view_mode': 'graph',
                'target': 'new',
                'domain': [
                    ('start_datetime', '>=', fields.Date.today()),
                    ('start_datetime', '<', fields.Date.today() + timedelta(days=1))
                ],
                'context': {
                    'graph_groupbys': ['start_datetime'],
                    'graph_measures': ['__count__'],
                    'graph_type': 'line'
                }
            }
        elif self.dashboard_type == 'recent_alerts':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Alertas recientes',
                'res_model': 'monitoreo.alert',
                'view_mode': 'tree,form',
                'target': 'new',
                'domain': [
                    ('create_date', '>=', fields.Datetime.now() - timedelta(days=7))
                ]
            }
        # Fallback to open the same record form to avoid no-op
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dashboard',
            'res_model': 'monitoreo.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
