from odoo import models, fields

class ProjectScope(models.Model):
    _name = 'project.scope'
    _description = 'Project Scope'

    name = fields.Char(string="Nombre", required=True)
    description = fields.Text(string="Descripción")
    project_id = fields.Many2one('project.project', string="Proyecto", ondelete="cascade")
