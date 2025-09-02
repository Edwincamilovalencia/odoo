from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import datetime, timedelta, date, time
from dateutil.relativedelta import relativedelta

class StockPickingExt(models.Model):

    _inherit = 'stock.picking'

    project_id = fields.Many2one('project.project', string='Proyecto')