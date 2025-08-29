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
    
    @api.model
    def init(self):
        """Actualizar títulos y descripciones del dashboard al instalar/actualizar módulo"""
        # Buscar y actualizar registros existentes
        dashboard_data = {
            'calls_by_day': {
                'name': 'Llamadas por día - Total llamadas actuales',
                'description': 'Cantidad total de llamadas registradas en el sistema'
            },
            'agent_states': {
                'name': 'Estados de agentes - Total agentes actuales', 
                'description': 'Cantidad de agentes únicos que han realizado llamadas'
            },
            'calls_by_hour': {
                'name': 'Distribución por hora - Total llamadas',
                'description': 'Total de llamadas y distribución por hora del día'
            },
            'recent_alerts': {
                'name': 'Alertas - Total alertas recientes',
                'description': 'Cantidad de alertas generadas en los últimos días'
            }
        }
        
        for dashboard_type, data in dashboard_data.items():
            dashboard = self.search([('dashboard_type', '=', dashboard_type)], limit=1)
            if dashboard:
                dashboard.write(data)

    @api.depends('dashboard_type')
    def _compute_count(self):
        for record in self:
            if record.dashboard_type == 'calls_by_day':
                # Total de llamadas registradas
                record.count = self.env['retain.call.history'].search_count([])
            elif record.dashboard_type == 'agent_states':
                # Total de agentes únicos que han hecho llamadas
                agents = self.env['retain.call.history'].read_group(
                    domain=[('agent_name', '!=', False)],
                    fields=['agent_name'],
                    groupby=['agent_name']
                )
                record.count = len(agents)
            elif record.dashboard_type == 'calls_by_hour':
                # Total de llamadas del sistema (sin importar dirección)
                record.count = self.env['retain.call.history'].search_count([])
            elif record.dashboard_type == 'recent_alerts':
                # Total de alertas pendientes
                record.count = self.env['monitoreo.alert'].search_count([
                    ('state', '=', 'pending')
                ])
            else:
                record.count = 0

    def action_open_dashboard(self):
        """Abrir el dashboard correspondiente"""
        self.ensure_one()
        if self.dashboard_type == 'calls_by_day':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Llamadas por día',
                'res_model': 'retain.call.history',
                'view_mode': 'graph,tree,form',
                'target': 'new',
                'context': {
                    'graph_groupbys': ['call_date:day'],
                    'graph_measures': ['__count__'],
                    'graph_type': 'bar'
                }
            }
        elif self.dashboard_type == 'agent_states':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Agentes por llamadas',
                'res_model': 'retain.call.history',
                'view_mode': 'graph,tree,form',
                'target': 'new',
                'context': {
                    'graph_groupbys': ['agent_name'],
                    'graph_measures': ['__count__'],
                    'graph_type': 'bar'
                }
            }
        elif self.dashboard_type == 'calls_by_hour':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Llamadas por hora',
                'res_model': 'retain.call.history',
                'view_mode': 'graph,tree,form',
                'target': 'new',
                'context': {
                    'graph_groupbys': ['call_hour'],
                    'graph_measures': ['__count__'],
                    'graph_type': 'bar'
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
                    ('state', '=', 'pending')
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
