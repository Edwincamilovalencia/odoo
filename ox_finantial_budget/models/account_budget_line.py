# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

class AccountBudgetLine(models.Model):

    _name = 'account.budget.line'
    _description = 'Linea de presupuesto'

    budget_id = fields.Many2one('account.budget', string='Presupuesto')
    budget_item_id = fields.Many2one('account.budget.item', string='Rubro presupuestal')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Centro Costo')
    planned_amount = fields.Float(string='PPTO', required=True)
    executed_amount = fields.Float(string='Ejec.', compute='_compute_budget_execution', store=True)
    theoretical_value = fields.Float(string='Saldo', compute='_compute_budget_execution', store=True)
    executed_por_amount = fields.Float(string='% Ejec.', compute='_compute_budget_execution', store=True)
    type = fields.Selection(string='Tipo', selection=[('income', 'Ingreso'), ('expense', 'Gasto / Costo')])
    project_id = fields.Many2one('project.project', string='Proyecto')
    user_id = fields.Many2one('res.users', string='Responsable')
    monthly_budget = fields.Boolean(string="Presupuesto mensual", default=False, store=True)
    budget_state = fields.Selection(related="budget_id.state", string="Estado del Presupuesto", store=True)

    budget_month = fields.Float(string='PPTO Mes.', compute="_compute_budget_month", store=True)
    planned_amount_month_accumulated = fields.Float(string='PPTO Acum.')
    executed_amount_month_accumulated = fields.Float(string='Ejec. Acum.')
    theoretical_value_month_accumulated = fields.Float(string='Saldo Acum.')
    executed_por_amount_month_accumulated = fields.Float(string='% Ejec. Acum.')

    # Campos para cada mes
    budget_january = fields.Float(string="Enero", store=True)
    budget_february = fields.Float(string="Febrero", store=True)
    budget_march = fields.Float(string="Marzo", store=True)
    budget_april = fields.Float(string="Abril", store=True)
    budget_may = fields.Float(string="Mayo", store=True)
    budget_june = fields.Float(string="Junio", store=True)
    budget_july = fields.Float(string="Julio", store=True)
    budget_august = fields.Float(string="Agosto", store=True)
    budget_september = fields.Float(string="Septiembre", store=True)
    budget_october = fields.Float(string="Octubre", store=True)
    budget_november = fields.Float(string="Noviembre", store=True)
    budget_december = fields.Float(string="Diciembre", store=True)

    comparison_status = fields.Selection([('N', 'Normal'),('M', 'Modificado'),('D', 'Eliminado')], string='Estado Comparación', default='N')
    
    @api.depends('budget_item_id.account_ids', 'budget_id.date_start', 'budget_id.date_end', 'budget_item_id.type', 'budget_month', 'budget_id.month_selection')
    def _compute_budget_execution(self):
        for record in self:
            executed_amount = 0.0
            budget_value = record.budget_month if record.budget_month else record.planned_amount

            if record.budget_item_id.account_ids:
                domain = [
                    ('account_id', 'in', record.budget_item_id.account_ids.ids),
                    ('date', '>=', record.budget_id.date_start),
                    ('date', '<=', record.budget_id.date_end),
                    ('move_id.state', '=', 'posted')
                ]

                # Filtrar por mes si `budget_month` tiene un valor
                if record.budget_month:
                    selected_month = record.budget_id.month_selection
                    if selected_month:
                        year = fields.Date.today().year  # Asumimos el año actual
                        first_day = fields.Date.from_string(f"{year}-{selected_month}-01")
                        last_day = first_day + relativedelta(months=1, days=-1)
                        domain.append(('date', '>=', first_day))
                        domain.append(('date', '<=', last_day))

                # Filtrar por tipo de rubro (Débito o Crédito)
                if record.budget_item_id.type == 'debit':
                    domain.append(('debit', '>', 0))
                else:
                    domain.append(('credit', '>', 0))

                # Filtrar por cuenta analítica si está definida
                if record.analytic_account_id:
                    domain.append(('analytic_distribution', 'ilike', record.analytic_account_id.id))
                else:
                    domain.append(('analytic_distribution', '=', False))

                moves = self.env['account.move.line'].search(domain)

                for move in moves:
                    analytic_distribution = move.analytic_distribution or {}
                    if record.analytic_account_id:
                        percentage = analytic_distribution.get(str(record.analytic_account_id.id), 0) / 100
                    else:
                        percentage = 1.0 if not analytic_distribution else 0.0

                    # Aplicar el monto correcto según el tipo de rubro
                    if record.budget_item_id.type == 'debit':
                        executed_amount += move.debit * percentage
                    else:
                        executed_amount += move.credit * percentage

            executed_amount = abs(executed_amount)

            # Aplicar los cálculos con `budget_month` si tiene valor
            if record.budget_month:
                record.executed_amount = executed_amount
                record.theoretical_value = record.budget_month - executed_amount
                record.executed_por_amount = (executed_amount / record.budget_month * 100) if record.budget_month else 0
            else:
                # Cálculo normal cuando `budget_month` es 0
                record.executed_amount = executed_amount
                record.theoretical_value = record.planned_amount - executed_amount
                record.executed_por_amount = (executed_amount / record.planned_amount * 100) if record.planned_amount else 0

    @api.depends('budget_january', 'budget_february', 'budget_march', 'budget_april','budget_may', 'budget_june', 'budget_july', 'budget_august','budget_september', 'budget_october', 'budget_november', 'budget_december','budget_id.month_selection', 'executed_amount')
    def _compute_budget_month(self):
        for record in self:
            month_mapping = {
                '01': record.budget_january,
                '02': record.budget_february,
                '03': record.budget_march,
                '04': record.budget_april,
                '05': record.budget_may,
                '06': record.budget_june,
                '07': record.budget_july,
                '08': record.budget_august,
                '09': record.budget_september,
                '10': record.budget_october,
                '11': record.budget_november,
                '12': record.budget_december,
            }
            selected_month = record.budget_id.month_selection
            record.budget_month = month_mapping.get(selected_month, 0.0)

            if not selected_month:
                # Si no hay mes seleccionado o el presupuesto del mes es 0, limpiamos valores
                record.planned_amount_month_accumulated = 0.0
                record.executed_amount_month_accumulated = 0.0
                record.theoretical_value_month_accumulated = 0.0
                record.executed_por_amount_month_accumulated = 0.0
                continue

            accumulated_budget = 0.0
            accumulated_execution = 0.0
            start_accumulation = False

            year = fields.Date.today().year  

            for month in sorted(month_mapping.keys()):
                budget_value = month_mapping[month]

                if budget_value > 0.0:
                    start_accumulation = True
                
                if start_accumulation:

                    first_day = fields.Date.from_string(f"{year}-{month}-01")
                    last_day = first_day + relativedelta(months=1, days=-1)

                    domain = [
                        ('account_id', 'in', record.budget_item_id.account_ids.ids),
                        ('date', '>=', first_day),
                        ('date', '<=', last_day),
                        ('move_id.state', '=', 'posted')
                    ]

                    if record.budget_item_id.type == 'debit':
                        domain.append(('debit', '>', 0))
                    else:
                        domain.append(('credit', '>', 0))

                    if record.analytic_account_id:
                        domain.append(('analytic_distribution', 'ilike', record.analytic_account_id.id))

                    moves = self.env['account.move.line'].search(domain)

                    executed_amount = 0.0

                    for move in moves:
                        analytic_distribution = move.analytic_distribution or {}

                        if record.analytic_account_id:
                            percentage = analytic_distribution.get(str(record.analytic_account_id.id), 0) / 100
                        else:
                            percentage = 1.0 if not analytic_distribution else 0.0

                        if record.budget_item_id.type == 'debit':
                            executed_amount += move.debit * percentage
                        else:
                            executed_amount += move.credit * percentage

                    accumulated_budget += budget_value
                    accumulated_execution += abs(executed_amount)

                if month == selected_month:
                    break 

            record.planned_amount_month_accumulated = accumulated_budget
            record.executed_amount_month_accumulated = accumulated_execution
            record.theoretical_value_month_accumulated = accumulated_budget - accumulated_execution
            record.executed_por_amount_month_accumulated = ((accumulated_execution / accumulated_budget * 100) if accumulated_budget else 0.0)

    #@api.constrains('budget_january', 'budget_february', 'budget_march', 'budget_april','budget_may', 'budget_june', 'budget_july', 'budget_august','budget_september', 'budget_october', 'budget_november', 'budget_december','planned_amount')
    #def _check_budget_allocation(self):
    #    for record in self:
    #        total_monthly = sum([
    #            record.budget_january, record.budget_february, record.budget_march,
    #            record.budget_april, record.budget_may, record.budget_june,
    #            record.budget_july, record.budget_august, record.budget_september,
    #            record.budget_october, record.budget_november, record.budget_december
    #        ])
    #        if total_monthly > record.planned_amount:
    #            raise ValidationError("La suma de los valores mensuales no puede superar el presupuesto principal.")

    @api.onchange('monthly_budget', 'budget_january', 'budget_february', 'budget_march', 'budget_april', 'budget_may', 'budget_june', 'budget_july', 'budget_august', 'budget_september', 'budget_october', 'budget_november', 'budget_december')
    def _onchange_monthly_budget(self):
        """Actualiza el presupuesto total basado en la sumatoria de los meses."""
        if self.monthly_budget:
            self.planned_amount = sum([
                self.budget_january, self.budget_february, self.budget_march,
                self.budget_april, self.budget_may, self.budget_june,
                self.budget_july, self.budget_august, self.budget_september,
                self.budget_october, self.budget_november, self.budget_december
            ])
        else:
            self.planned_amount = 0  # O dejarlo manual si se requiere


    def action_save_and_close(self):
        """ Guarda los valores y cierra el formulario. """
        return {'type': 'ir.actions.act_window_close'}

    def action_account_budget_line_form(self):
        """Abre el formulario de la línea de presupuesto con datos existentes"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detalles de Línea de Presupuesto',
            'res_model': 'account.budget.line',
            'view_mode': 'form',
            'view_id': self.env.ref('ox_finantial_budget.view_budget_line_form').id,
            'res_id': self.id,
            'target': 'new',
        }
        