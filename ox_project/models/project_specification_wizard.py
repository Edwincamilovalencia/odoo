# models/project_specification_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProjectSpecificationWizard(models.TransientModel):
    _name = 'project.specification.wizard'
    _description = 'Pedir Especificaciones para el Proyecto'

    reason = fields.Text(string="Motivo", required=True)
    project_id = fields.Many2one('project.project', string="Proyecto", required=True)

    def action_submit_reason(self):
        self.ensure_one()
        if self.env.user not in self.project_id.approver_ids:
            raise UserError("No tienes permiso para solicitar especificaciones.")

        self.project_id.message_post(
            body=f"<b>Motivo por el que se pidieron especificaciones:</b><br/>{self.reason}",
            message_type="comment"
        )

        self.project_id.write({
            'state': 'planeacion',
            'approval_status': 'rejected',
            'approved_by': [(5, 0, 0)],  # Limpia los aprobadores
        })
