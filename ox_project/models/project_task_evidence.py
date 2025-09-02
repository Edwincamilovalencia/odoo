from odoo import models, fields

class ProjectTaskEvidence(models.Model):
    _name = 'project.task.evidence'
    _description = 'Evidencia de Tarea'

    task_id = fields.Many2one('project.task', string='Tarea')
    name = fields.Char(string='Nombre de la Evidencia', required=True)
    file = fields.Binary(string='Archivo')
    filename = fields.Char(string='Nombre de Archivo')
