# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

class AccountBudgetItem(models.Model):

    _name = 'account.budget.item'
    _description = 'Rubro presupuestal'

    name = fields.Char(string='Rubro presupuestal')
    account_ids = fields.Many2many('account.account', 'budget_account_rel', 'budget_id', 'account_id', string='')
    type = fields.Selection([('debit', 'Débito'), ('credit', 'Crédito')], string='Tipo', required=True, default='debit')