from odoo import models, fields

class ProjectStakeholder(models.Model):
    _name = 'project.stakeholder'
    _description = 'Stakeholder del Proyecto'

    name = fields.Char('Nombre', required=True)
    email = fields.Char('Correo')
    role = fields.Char('Rol')
    phone = fields.Char('Teléfono')
    project_id = fields.Many2one('project.project', string='Proyecto', required=True)
