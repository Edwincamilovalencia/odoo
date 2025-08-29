from odoo import models, fields, api

class ProjectApprovalHistory(models.Model):
    _name = 'project.approval.history'
    _description = 'Historial de Aprobaciones del Proyecto'

    project_id = fields.Many2one('project.project', string="Proyecto", required=True, ondelete='cascade')
    approver_id = fields.Many2one('res.users', string="Aprobador", required=True)
    approval_date = fields.Datetime(string="Fecha de Aprobación", default=fields.Datetime.now)
