# -*- coding: utf-8 -*-
"""
Modelo: monitoreo.alert
Registra alertas generadas por el sistema de monitoreo.
"""
from odoo import models, fields, api, _
from datetime import timedelta

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

    @api.model
    def check_daily_calls(self):
        """
        Método para verificar si hay llamadas del día y generar alertas si no las hay.
        Este método debe ser llamado por un cron job diario.
        """
        from datetime import datetime
        
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        
        # Convertir fechas a datetime para la comparación
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        today_start = datetime.combine(today, datetime.min.time())
        
        # Verificar si hubo llamadas ayer
        calls_yesterday = self.env['retain.call.history'].search_count([
            ('call_date', '>=', yesterday_start),
            ('call_date', '<', today_start)
        ])
        
        # Si no hubo llamadas ayer, crear una alerta
        if calls_yesterday == 0:
            # Verificar si ya existe una alerta similar reciente
            existing_alert = self.search([
                ('alert_type', '=', 'system_error'),
                ('name', 'ilike', 'Sin llamadas registradas'),
                ('date', '>=', yesterday),
                ('state', '=', 'pending')
            ], limit=1)
            
            if not existing_alert:
                self.create({
                    'name': f'Sin llamadas registradas el {yesterday.strftime("%d/%m/%Y")}',
                    'alert_type': 'system_error',
                    'severity': 'warning',
                    'state': 'pending',
                    'description': f'No se registraron llamadas durante todo el día {yesterday.strftime("%d de %B de %Y")}. '
                                   f'Esto podría indicar un problema en el sistema o falta de actividad.'
                })
        
        return True

    def action_test_daily_check(self):
        """
        Método manual para probar la verificación de llamadas diarias.
        """
        return self.check_daily_calls()
