# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class LlamadaSettings(models.Model):
    _name = 'llamada.settings'
    _description = 'Ajustes de vinculación de agentes'

    # Campos principales
    name = fields.Many2one('res.partner', string='Persona', required=True)
    agent_name = fields.Many2many('retain.call.history', string='Agentes asignados')
    agent_names_display = fields.Char(string='Nombres de agentes', compute='_compute_agent_names_display', store=False)

    # Mostrar los nombres únicos de agentes asignados en la vista lista
    @api.depends('agent_name')
    def _compute_agent_names_display(self):
        for record in self:
            unique_agent_names = list(set(record.agent_name.mapped('agent_name')))
            unique_agent_names = [agent_name for agent_name in unique_agent_names if agent_name]
            record.agent_names_display = ', '.join(unique_agent_names) if unique_agent_names else ''

    # Validación automática para evitar agentes duplicados
    @api.constrains('agent_name')
    def _check_unique_agents(self):
        for record in self:
            if record.agent_name:
                agent_names = record.agent_name.mapped('agent_name')
                agent_names = [agent_name for agent_name in agent_names if agent_name]


    # Acción para mostrar notificación al guardar andres.torres@demo.com
    def action_save_agents(self):
        agent_names = self.agent_name.mapped('agent_name')
        agent_names = [agent_name for agent_name in agent_names if agent_name]
        if len(agent_names) != len(set(agent_names)):
            mensaje = 'No se puede asignar el mismo agente dos veces a una persona.'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': mensaje,
                    'type': 'danger',
                    'sticky': False,
                }
            }
        self.ensure_one()
        self.write({'agent_name': [(6, 0, self.agent_name.ids)]})
        mensaje = 'Agentes correctamente asignados.'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': mensaje,
                'type': 'success',
                'sticky': False,
            }
        }
