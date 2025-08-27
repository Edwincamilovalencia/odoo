# -*- coding: utf-8 -*-
"""
Modelo: monitoreo.alert
Registra alertas generadas por el sistema de monitoreo.
"""
from odoo import models, fields, api, _

class MonitoreoAlert(models.Model):
    _name = 'monitoreo.alert'
    _description = 'Alerta de Monitoreo'
    _order = 'date desc'

    date = fields.Datetime(string='Fecha', default=fields.Datetime.now, required=True)
    name = fields.Char(string='Alerta', required=True)
    alert_type = fields.Selection([
        ('agent_offline', 'Agente desconectado'),
        ('call_failed', 'Llamada fallida'),
        ('system_error', 'Error del sistema'),
        ('performance', 'Rendimiento'),
    ], string='Tipo de Alerta', required=True)
    severity = fields.Selection([
        ('warning', 'Advertencia'),
        ('critical', 'Crítica'),
    ], string='Severidad', required=True)
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('resolved', 'Resuelta'),
    ], string='Estado', default='pending', required=True)
    description = fields.Text(string='Descripción')
    resolution = fields.Text(string='Resolución')
    agent_id = fields.Many2one('monitoreo.agent', string='Agente Relacionado')
    resolved_date = fields.Datetime(string='Fecha de Resolución')
    resolved_by = fields.Many2one('res.users', string='Resuelto por')

    def action_mark_resolved(self):
        """
        Marca la alerta como resuelta.
        """
        for alert in self:
            if alert.state != 'resolved':
                alert.write({
                    'state': 'resolved',
                    'resolved_date': fields.Datetime.now(),
                    'resolved_by': self.env.user.id,
                })
