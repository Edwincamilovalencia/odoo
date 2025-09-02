from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class ProjectTask(models.Model):
    _inherit = 'project.task'

    specific_objective_id = fields.Many2one('project.specific.objective', string='Objetivo Específico')
    project_id = fields.Many2one('project.project', string='Proyecto') 
    dependent_task_ids = fields.Many2many('project.task','task_dependency_rel','task_id','dependent_task_id',string='Tareas dependientes')
    state = fields.Selection([('pending', 'Pendiente'),('in_progress', 'En Proceso'),('done', 'Completada'),('cancelled', 'Cancelada')
    ], string='Estado', default='pending', tracking=True)
    activity_deadline = fields.Date(string='Fecha de la actividad')
    is_activity_done = fields.Boolean(string='Actividad finalizada', default=False)
    task_ids = fields.One2many('project.task','specific_objective_id',string='Actividades')
    material_budget_ids = fields.One2many('project.material.budget','task_id',string='Materiales de esta tarea')
    show_request_button = fields.Boolean(default=True)  # Controla la visibilidad del botón "Solicitar"
    show_entry_button = fields.Boolean(default=True)  # Controla la visibilidad del botón "Registrar Entrada"
    evidence_ids = fields.One2many('project.task.evidence', 'task_id', string='Evidencias')
    progress_percentage = fields.Integer(string="Progreso",compute='_compute_progress_percentage',store=True,group_operator="avg")
    
    # verificacion de objetivo especifico

    def write(self, vals):
        for record in self:
            new_state = vals.get('state', record.state)
            specific_objective = vals.get('specific_objective_id', record.specific_objective_id)

            if new_state != 'pending' and not specific_objective:
                raise UserError("Debes asignar un Objetivo Específico antes de cambiar el estado de la tarea.")

        return super().write(vals)

    @api.depends('state')
    def _compute_progress_percentage(self):
        for task in self:
            if task.state == 'pending':
                task.progress_percentage = 30
            elif task.state == 'in_progress':
                task.progress_percentage = 50
            elif task.state == 'done':
                task.progress_percentage = 100
            elif task.state == 'cancelled':
                task.progress_percentage = 0
            else:
                task.progress_percentage = 0
                
                
    def action_finish_activity(self):
        for task in self:
            incomplete_dependencies = task.depends_on_ids.filtered(lambda t: t.state != 'done')
            if incomplete_dependencies:
                dep_names = ', '.join(incomplete_dependencies.mapped('name'))
                raise UserError(f'No puedes finalizar esta actividad hasta que se completen las siguientes tareas: {dep_names}')
            task.state = 'done'
            # Aquí puedes agregar la lógica para actualizar el avance del objetivo


    def _update_objective_progress(self):
        """Actualiza el porcentaje de avance del objetivo específico."""
        for task in self:
            objective = task.specific_objective_id
            if objective:
                total = len(objective.task_ids)
                done = len(objective.task_ids.filtered(lambda t: t.is_activity_done))
                objective.progress = (done / total) * 100 if total else 0

    def action_start_activity(self):
            for task in self:
                task.state = 'in_progress'

    def action_finish_activity(self):
            for task in self:
                task.state = 'done'
                # Aquí puedes llamar a la función que actualiza el objetivo específico

    def action_cancel_activity(self):
            for task in self:
                task.state = 'cancelled'
