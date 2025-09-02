# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import re

class AccountBudget(models.Model):

    _name = 'account.budget'
    _description = 'Presupuesto'
    _sql_constraints = [('unique_budget_name', 'UNIQUE(name)', 'El nombre del presupuesto debe ser único.')]

    name = fields.Char(string='Nombre presupuesto', required=True)
    date_start = fields.Date(string='Fecha inicial', required=True)
    date_end = fields.Date(string='Fecha final', required=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True)
    budget_type = fields.Selection(string='Tipo', selection=[('finantial', 'Financiero'), ('project', 'Proyecto')], default='finantial', required=True)
    project_id = fields.Many2one('project.project', string='Proyecto')
    state = fields.Selection(string='Estado', selection=[('draft', 'Borrador'), ('active', 'Activo'), ('closed', 'Cerrado')], default='draft')
    budget_line_ids = fields.One2many('account.budget.line', inverse_name='budget_id', string='Lineas del presupuesto')
    from_other_mod = fields.Boolean(string='Desde otro modulo')
    month_selection = fields.Selection(
        selection=[('01', 'Enero'),('02', 'Febrero'),('03', 'Marzo'),('04', 'Abril'),('05', 'Mayo'),('06', 'Junio'),
            ('07', 'Julio'),('08', 'Agosto'),('09', 'Septiembre'),('10', 'Octubre'),('11', 'Noviembre'),('12', 'Diciembre')],string="Mes")

    parent_id = fields.Many2one('account.budget', string="Presupuesto Original")
    child_ids = fields.One2many('account.budget', 'parent_id', string="Versiones")
    
    def action_active_budget(self):
        """Activa el presupuesto si todas las líneas tienen valores válidos."""
        for line in self.budget_line_ids:
            if line.planned_amount <= 0:
                raise ValidationError('No se puede iniciar el presupuesto con líneas en 0 o vacías.')
        
        self.state = 'active'
        for line in self.budget_line_ids:
            line._compute_budget_execution()

    def action_cancel_budget(self):
        """Restablece el presupuesto al estado de borrador y reinicia valores."""
        self.state = 'draft'
        for line in self.budget_line_ids:
            line.executed_amount = 0
            line.theoretical_value = line.planned_amount   

    def action_refresh_budget(self):
        """Recalcula la ejecución del presupuesto en todas las líneas."""
        for line in self.budget_line_ids:
            line._compute_budget_execution()

    def action_create_new_version(self):
        """Crea una nueva versión del presupuesto actual con los mismos datos del padre y la enlaza como hijo."""
        for budget in self:
            original_budget = budget.parent_id or budget

            base_name = original_budget.name 
            
            # Obtener la última versión
            version_numbers = [
                int(re.search(r' v(\d+)$', b.name).group(1)) 
                for b in original_budget.child_ids if re.search(r' v(\d+)$', b.name)
            ]
            new_version = max(version_numbers, default=1) + 1  

            new_name = f"{base_name} v{new_version}" 

            # Crear la nueva versión con el presupuesto original como padre
            new_budget = budget.copy(default={
                'name': new_name,
                'parent_id': original_budget.id,  
                'budget_line_ids': False 
            })

            # Copiar las líneas del presupuesto original a la nueva versión
            new_lines = []
            for line in original_budget.budget_line_ids:
                new_line = line.copy(default={'budget_id': new_budget.id})
                new_lines.append(new_line.id)

            new_budget.budget_line_ids = [(6, 0, new_lines)] 

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.budget',
                'view_mode': 'form',
                'res_id': new_budget.id,
                'target': 'current',
            }

        
    def action_compare_versions(self):
        """ Compara el presupuesto actual con su última versión """
        for budget in self:
            if not budget.child_ids:
                for line in budget.budget_line_ids:
                    line.comparison_status = 'N'
                return True

            latest_version = budget.child_ids.sorted(lambda v: v.create_date, reverse=True)[0]

            # Crear diccionarios de líneas con la clave (budget_item_id, analytic_account_id)
            original_lines = {
                (line.budget_item_id.id, line.analytic_account_id.id if line.analytic_account_id else None): line
                for line in budget.budget_line_ids
            }
            latest_lines = {
                (line.budget_item_id.id, line.analytic_account_id.id if line.analytic_account_id else None): line
                for line in latest_version.budget_line_ids
            }

            # Comparar líneas
            for key, line in original_lines.items():
                if key not in latest_lines:
                    line.comparison_status = 'D' 
                elif line.planned_amount != latest_lines[key].planned_amount:
                    line.comparison_status = 'M' 
                else:
                    line.comparison_status = 'N' 

        return True