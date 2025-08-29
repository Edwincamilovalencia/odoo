from odoo import models, fields, api

class SpecificObjective(models.Model):
    _name = 'project.specific.objective'
    _description = 'Objetivo Específico'

    name = fields.Char()
    project_id = fields.Many2one('project.project', string='Proyecto')  
    task_ids = fields.One2many('project.task', 'specific_objective_id', string='Actividades')
    task_count = fields.Integer(string='Número de Tareas', compute='_compute_task_count')
    progress_percentage = fields.Integer(string="Porcentaje de cumplimiento",compute="_compute_progress_percentage",store=True)
    progress_display = fields.Char(string="Cumplimiento (%)",compute="_compute_progress_percentage",store=True)

    @api.depends('task_ids')
    def _compute_task_count(self):
        for obj in self:
            obj.task_count = len(obj.task_ids)

    def open_tasks_from_objective(self):
        # Tu lógica aquí, por ejemplo abrir las tareas asociadas
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tareas',
            'res_model': 'project.task',
            'view_mode': 'tree,form',
            'domain': [('specific_objective_id', '=', self.id)],
        }
    @api.depends('task_ids.state')
    def _compute_progress_percentage(self):
        for obj in self:
            total = len(obj.task_ids)
            if total > 0:
                done_count = len(obj.task_ids.filtered(lambda t: t.state == 'done'))
                percentage = int((done_count / total) * 100)
            else:
                percentage = 0
            obj.progress_percentage = percentage
            obj.progress_display = f"{percentage}%"