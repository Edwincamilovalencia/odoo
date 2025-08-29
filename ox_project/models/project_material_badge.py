from odoo import models, fields, api
from odoo.exceptions import UserError

class ProjectMaterialBudget(models.Model):
    _name = 'project.material.budget'
    _description = 'Material presupuestado'

    project_id = fields.Many2one('project.project', string='Proyecto')
    name = fields.Many2one('product.product', string='Elemento', required=True)
    qty = fields.Float(string='Cantidad', default=0)
    estimed_coste = fields.Float(string='Costo Estimado', compute="_compute_estimed_coste", store=True)
    task_id = fields.Many2one('project.task', string='Tarea')
    warehouse_id = fields.Many2one('stock.warehouse', string='Bodega')
    qty_available = fields.Float(string='Disponibles', compute='_compute_qty_available', store=True)
    show_request_button = fields.Boolean(compute='_compute_show_buttons')
    show_entry_button = fields.Boolean(compute='_compute_show_buttons')



    @api.depends('name', 'qty')
    def _compute_estimed_coste(self):
        """ Calcula el costo estimado automáticamente cuando se ingresa la cantidad """
        for record in self:
            if record.name and record.qty > 0:
                record.estimed_coste = record.qty * record.name.standard_price
            else:
                record.estimed_coste = 0

    def action_solicitar_material(self):
        """ Crea un borrador de transferencia en el inventario """
        if not self:
            raise UserError("No hay registros seleccionados para procesar.")

        stock_picking = self.env['stock.picking'].create({
            'partner_id': self.env.user.company_id.partner_id.id,  # Empresa responsable
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,  # Tipo: Interno
            'location_id': self.env.ref('stock.stock_location_stock').id,  # Desde Almacén
            'location_dest_id': self.env.ref('stock.stock_location_output').id,  # Hacia Salida
            'move_ids_without_package': [(0, 0, {
                'name': record.name.display_name,
                'product_id': record.name.id,
                'product_uom_qty': record.qty,
                'product_uom': record.name.uom_id.id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_output').id,
            }) for record in self if record.qty > 0]
        })

        if not stock_picking.move_ids_without_package:
            raise UserError("Debe ingresar al menos un producto con cantidad válida.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Transferencia de Material',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': stock_picking.id,
            'target': 'current',
        }
    @api.depends('name', 'warehouse_id')
    def _compute_qty_available(self):
        for record in self:
            if record.name and record.warehouse_id:
                stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', record.name.id),
                    ('location_id', 'child_of', record.warehouse_id.view_location_id.id)
                ], limit=1)
                record.qty_available = stock_quant.quantity if stock_quant else 0
            else:
                record.qty_available = 0

    @api.depends('qty', 'qty_available')
    def _compute_show_buttons(self):
        for record in self:
            record.show_request_button = record.qty > record.qty_available
            record.show_entry_button = record.qty_available == 0

    def action_registrar_entrada(self):
        """ Redirige al usuario a un formulario de entrada manual de material """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Crear Entrada de Inventario',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'context': {
                'default_picking_type_id': self.env.ref('stock.picking_type_internal').id,
                'default_location_id': self.env.ref('stock.stock_location_output').id,
                'default_location_dest_id': self.env.ref('stock.stock_location_stock').id,
            },
            'target': 'current',
        }

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.warehouse_id:
            quants = self.env['stock.quant'].search([
                ('location_id', 'child_of', self.warehouse_id.view_location_id.id),
                ('quantity', '>', 0)
            ])
            product_ids = quants.mapped('product_id').ids
            return {
                'domain': {
                    'name': [('id', 'in', product_ids)]
                }
            }
        else:
            return {
                'domain': {
                    'name': []
                }
            }
