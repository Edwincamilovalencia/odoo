from odoo import models, fields
class ProjectSpecificActivity(models.Model):
    _name = 'project.specific.activity'
    _description = 'Actividad del Objetivo Específico'

    name = fields.Char(string="Nombre de la Actividad", required=True)
    description = fields.Text(string="Descripción")
    task_id = fields.Many2one('project.task', string="Tarea", required=True)
    objective_id = fields.Many2one('project.specific.objective', string="Objetivo Específico", required=True)
    start_date = fields.Date(string="Fecha de Inicio")
    end_date = fields.Date(string="Fecha de Fin")
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('in_progress', 'En Proceso'),
        ('completed', 'Completada'),
    ], string="Estado", default='pending')
