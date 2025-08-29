from odoo import models, fields

class ProjectType(models.Model):
    _name = "project.type"
    _description = "Project Type"

    name = fields.Char(string="Nombre", required=True)
    description = fields.Text(string="Descripción")
