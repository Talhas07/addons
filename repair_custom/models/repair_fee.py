from odoo import api, fields, models, _

class RepairOrder(models.Model):
    _inherit = 'repair.order'

    fees_lines = fields.One2many(
        'repair.fee', 'repair_id', 'Operations',
        copy=True, readonly=False)

class RepairFee(models.Model):
    _name = 'repair.fee'
    _description = 'Repair Fees'

    repair_id = fields.Many2one(
        'repair.order', 'Repair Order Reference',
        index=True, ondelete='cascade', required=True)
    company_id = fields.Many2one(
        related="repair_id.company_id", index=True, store=True)
    currency_id = fields.Many2one(
        related="repair_id.company_id.currency_id")
    name = fields.Text('Description', index=True, required=True)
    product_id = fields.Many2one(
        'product.product', 'Product', check_company=True,
        domain="[('type', '=', 'service'), '|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    product_uom_qty = fields.Float('Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price')
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_total_and_subtotal', store=True, digits=0)
    price_total = fields.Float('Total', compute='_compute_price_total_and_subtotal', store=True, digits=0)
    tax_id = fields.Many2many(
        'account.tax', 'repair_fee_line_tax', 'repair_fee_line_id', 'tax_id', 'Taxes',
        domain="[('type_tax_use','=','sale'), ('company_id', '=', company_id)]", check_company=True)
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line', copy=False, readonly=True, check_company=True)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)

    @api.depends('price_unit', 'repair_id', 'product_uom_qty', 'product_id', 'tax_id')
    def _compute_price_total_and_subtotal(self):
        for fee in self:
            taxes = fee.tax_id.compute_all(fee.price_unit, fee.currency_id, fee.product_uom_qty, fee.product_id, fee.repair_id.partner_id)
            fee.price_subtotal = taxes['total_excluded']
            fee.price_total = taxes['total_included']
