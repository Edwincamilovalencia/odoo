from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import datetime, timedelta, date, time
from dateutil.relativedelta import relativedelta
import logging


class ProjectProjectExt(models.Model):
    _inherit = 'project.project'

    helpdesk_ticket_count = fields.Integer(
        string="Tickets",
        compute="_compute_helpdesk_ticket_count"
    )

    justification = fields.Html(help="Project justification")
    other_specifications = fields.Html(help="Additional project specifications")
    
    budgets_count = fields.Integer('Presupuesto', compute='_compute_budget_count', compute_sudo=True)
    project_ids = fields.One2many('account.budget', inverse_name='project_id', string='Proyectos')
    pickings_count = fields.Integer('Órdenes de Almacén', compute='_compute_pickings_count', compute_sudo=True)
    pickings_ids = fields.One2many('stock.picking', inverse_name='project_id', string='Órdenes de Almacén')
    cronograma = fields.Binary(string="Cronograma", help="Adjunta el cronograma del proyecto.")
    general_objectives = fields.Text(string="Objetivos Generales")
    scope_ids = fields.One2many('project.scope', 'project_id', string="Alcance")
    specific_objectives_ids = fields.One2many('project.specific.objective', 'project_id', string="Objetivos Específicos")
    approval_status = fields.Selection([('pending', 'Pendiente'),('approved', 'Aprobado'),('rejected', 'Rechazado')], string="Estado de Aprobación", default='pending', tracking=True)
    project_type_id = fields.Many2one("project.type", string="Tipo de Proyecto")
    state = fields.Selection([('planeacion', 'Planeación'),('en_aprobacion', 'En Aprobación'),('ejecucion', 'Ejecución'),('finalizado', 'Finalizado')], string="Estado", default='planeacion', tracking=True)
    approved_by = fields.Many2many('res.users','project_project_approved_by_rel','project_id','user_id',string="Aprobado por")
    _logger = logging.getLogger(__name__)  # Definir el logger dentro de la clase
    approval_history_ids = fields.One2many(    'project.approval.history', 'project_id', string="Historial de Aprobaciones")
    can_approve = fields.Boolean(string="Puede Aprobar",compute="_compute_can_approve",store=False)
    approver_ids = fields.Many2many('res.users','project_project_approver_ids_rel','project_id','user_id',string="Aprobadores")
    stakeholder_ids = fields.One2many('project.stakeholder','project_id',string='Stakeholders')
    @api.depends('approver_ids', 'state', 'approved_by')
    def _compute_can_approve(self):
        for project in self:
            project.can_approve = (
                project.state == 'en_aprobacion' and 
                self.env.user in project.approver_ids and
                self.env.user not in project.approved_by
        )
            

    @api.model
    def _group_expand_state(self, states, domain, order):
     return [state[0] for state in self._fields['state'].selection]

    state = fields.Selection([
    ('planeacion', 'Planeación'),
    ('en_aprobacion', 'En Aprobación'),
    ('ejecucion', 'Ejecución'),
    ('finalizado', 'Finalizado')
], group_expand='_group_expand_state', string="Estado", default='planeacion', tracking=True)




    @api.depends('approver_ids', 'state')
    def _compute_can_approve(self):
        for project in self:
            project.can_approve = (
            project.state == 'en_aprobacion' and 
            self.env.user in project.approver_ids and
            self.env.user not in project.approved_by
        )
        self._logger.info(
            f"User {self.env.user.id} can approve project {project.id}: {project.can_approve}"
        )

    def action_submit_for_approval(self):
        for project in self:
         if not project.approver_ids:
            raise UserError("Debes asignar aprobadores antes de enviar a aprobación.")
        project.write({
            'state': 'en_aprobacion',
            'approved_by': [(5, 0, 0)],  # Limpiar aprobaciones previas
            'approval_status': 'pending'
        })

    def action_approve(self):
        self.ensure_one()

    # Validar si el usuario es aprobador
        if self.env.user not in self.approver_ids:
            raise UserError("No tienes permiso para aprobar este proyecto.")

    # Evitar aprobaciones duplicadas
        if self.env.user in self.approved_by:
            raise UserError("Ya has aprobado este proyecto.")

    # Agregar al historial de aprobaciones
        self.env['project.approval.history'].create({
            'project_id': self.id,
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })

    # Agregar usuario a la lista de aprobadores
        self.write({
            'approved_by': [(4, self.env.user.id)]
        })

   # Verificar si todos los aprobadores ya aprobaron
        approved_users = set(self.approved_by.ids)
        required_approvers = set(self.approver_ids.ids)

        if approved_users == required_approvers:
            self.write({
                'approval_status': 'approved',
            'state': 'ejecucion'
    })
        else:
    # NO cambies el estado, simplemente sigue mostrando los aprobadores confirmados
            pass


    def action_request_specifications(self):
        self.ensure_one()
        if self.env.user not in self.approver_ids:
            raise UserError("No tienes permiso para solicitar especificaciones.")
        return {
            'name': 'Pedir Especificaciones',
            'type': 'ir.actions.act_window',
            'res_model': 'project.specification.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
            }
        }


    @api.depends('project_ids')
    def _compute_budget_count(self):
        for project in self:
            project.budgets_count = len(project.project_ids)

    @api.depends('pickings_ids')
    def _compute_pickings_count(self):
        for project in self:
            project.pickings_count = len(project.pickings_ids)

    @api.depends('helpdesk_ticket_count')
    def _compute_helpdesk_ticket_count(self):
        for project in self:
            project.helpdesk_ticket_count = self.env['helpdesk.ticket'].search_count([('project_id', '=', project.id)])

    def action_view_tickets(self):
        self.ensure_one()
        return {
            'name': 'Tickets',
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_budgets(self):
        self.ensure_one()

        # Validar que "Objetivos Generales" no esté vacío
        if not self.general_objectives:
            raise UserError("Debe completar el campo 'Objetivos Generales' antes de acceder a los presupuestos.")

        # Validar que "Alcance" tenga al menos un registro
        if not self.scope_ids:
            raise UserError("Debe agregar al menos un alcance antes de acceder a los presupuestos.")

        # Validar que "Objetivos Específicos" tenga al menos un registro
        if not self.specific_objectives_ids:
            raise UserError("Debe agregar al menos un objetivo específico antes de acceder a los presupuestos.")

        # Acción para abrir la vista de presupuestos
        action = self.env["ir.actions.actions"]._for_xml_id("ox_finantial_budget.account_budget_action")
        budget_ids = self.env['account.budget'].search([('project_id', '=', self.id)])
        action['domain'] = [('id', 'in', budget_ids.ids)]
        action['context'] = {'default_project_id': self.id, 'default_budget_type': 'project', 'default_from_other_mod': True}

        return action

    def action_view_pickings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_action")
        move_ids = self.env['stock.move'].search([('picking_id.project_id', '=', self.id)])
        action['domain'] = [('id', 'in', move_ids.ids)]
        return action

    
    def action_approve_project(self):
        for project in self:
            user = self.env.user
            # Validar que este usuario no haya aprobado antes
            already_approved = self.env['project.approval.history'].search([
                ('project_id', '=', project.id),
                ('approver_id', '=', user.id)
            ])
            if not already_approved:
                self.env['project.approval.history'].create({
                    'project_id': project.id,
                    'approver_id': user.id,
                    # approval_date se asigna automáticamente
                })

