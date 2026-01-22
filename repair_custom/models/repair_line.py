# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class RepairLine(models.Model):
    """Repair Line model for parts - legacy v16 compatibility"""
    _name = 'repair.line'
    _description = 'Repair Line (parts)'

    name = fields.Text('Description', required=True)
    repair_id = fields.Many2one(
        'repair.order', 'Repair Order Reference', required=True,
        index=True, ondelete='cascade', check_company=True)
    company_id = fields.Many2one(
        related='repair_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(
        related='repair_id.currency_id')
    type = fields.Selection([
        ('add', 'Add'),
        ('remove', 'Remove')], 'Type', default='add', required=True)
    product_id = fields.Many2one(
        'product.product', 'Product', required=True, check_company=True,
        domain="[('type', 'in', ['consu', 'product']), '|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price')
    price_subtotal = fields.Float(
        'Subtotal', compute='_compute_price_total_and_subtotal', store=True, digits=0)
    price_total = fields.Float(
        'Total', compute='_compute_price_total_and_subtotal', store=True, digits=0)
    tax_id = fields.Many2many(
        'account.tax', 'repair_operation_line_tax', 'repair_operation_line_id', 'tax_id', 'Taxes',
        domain="[('type_tax_use','=','sale'), ('company_id', '=', company_id)]", check_company=True)
    product_uom_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Product Unit of Measure', required=True)
    product_uom = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        compute='_compute_product_uom', store=True, readonly=False, precompute=True,
        required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    invoice_line_id = fields.Many2one(
        'account.move.line', 'Invoice Line',
        copy=False, readonly=True, check_company=True)
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        compute='_compute_location_id', store=True, readonly=False, precompute=True,
        index=True, required=True, check_company=True)
    location_dest_id = fields.Many2one(
        'stock.location', 'Dest. Location',
        compute='_compute_location_id', store=True, readonly=False, precompute=True,
        index=True, required=True, check_company=True)
    move_id = fields.Many2one(
        'stock.move', 'Inventory Move',
        copy=False, readonly=True)
    lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial',
        domain="[('product_id','=', product_id), ('company_id', '=', company_id)]", check_company=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], 'Status', default='draft',
        copy=False, readonly=True, required=True,
        help='The status of a repair line is set automatically to the one of the linked repair order.')
    tracking = fields.Selection(string='Product Tracking', related="product_id.tracking")

    @api.depends('price_unit', 'repair_id', 'product_uom_qty', 'product_id', 'tax_id', 'repair_id.invoice_method')
    def _compute_price_total_and_subtotal(self):
        for line in self:
            currency = line.repair_id.pricelist_id.currency_id if line.repair_id.pricelist_id else self.env.company.currency_id
            taxes = line.tax_id.compute_all(
                line.price_unit, currency, line.product_uom_qty,
                line.product_id, line.repair_id.partner_id)
            line.price_subtotal = taxes['total_excluded']
            line.price_total = taxes['total_included']

    @api.depends('product_id')
    def _compute_product_uom(self):
        for line in self:
            line.product_uom = line.product_id.uom_id.id

    @api.depends('type')
    def _compute_location_id(self):
        for line in self:
            if not line.type:
                line.location_id = False
                line.location_dest_id = False
            elif line.type == 'add':
                args = line.repair_id.company_id and [('company_id', '=', line.repair_id.company_id.id)] or []
                warehouse = line.env['stock.warehouse'].search(args, limit=1)
                line.location_id = warehouse.lot_stock_id
                line.location_dest_id = line.env['stock.location'].search(
                    [('usage', '=', 'production'), ('company_id', '=', line.repair_id.company_id.id)], limit=1)
            else:
                line.location_id = line.env['stock.location'].search(
                    [('usage', '=', 'production'), ('company_id', '=', line.repair_id.company_id.id)], limit=1).id
                line.location_dest_id = line.env['stock.location'].search(
                    [('scrap_location', '=', True), ('company_id', 'in', [line.repair_id.company_id.id, False])], limit=1).id

    @api.onchange('type')
    def onchange_operation_type(self):
        """On change of operation type."""
        if not self.type:
            pass
        elif self.type == 'add':
            self.onchange_product_id()
        else:
            self.price_unit = 0.0
            self.tax_id = False

    @api.onchange('repair_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """On change of product it sets product quantity, tax account, name, uom of product, unit price and price subtotal."""
        if not self.product_id or not self.product_uom_qty:
            return
        self = self.with_company(self.company_id)
        partner = self.repair_id.partner_id
        partner_invoice = self.repair_id.partner_invoice_id or partner
        if partner:
            self = self.with_context(lang=partner.lang)
        product = self.product_id
        self.name = product.display_name
        if product.description_sale:
            if partner:
                self.name += '\n' + self.product_id.with_context(lang=partner.lang).description_sale
            else:
                self.name += '\n' + self.product_id.description_sale
        if self.type != 'remove':
            if partner:
                fpos = self.env['account.fiscal.position']._get_fiscal_position(
                    partner_invoice, delivery=self.repair_id.partner_id)
                taxes = self.product_id.taxes_id.filtered(lambda x: x.company_id == self.repair_id.company_id)
                self.tax_id = fpos.map_tax(taxes)
            warning = False
            pricelist = self.repair_id.pricelist_id
            if not pricelist:
                warning = {
                    'title': _('No pricelist found.'),
                    'message': _('You have to select a pricelist in the Repair form !\n Please set one before choosing a product.')
                }
                return {'warning': warning}
            else:
                self._onchange_product_uom()

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        pricelist = self.repair_id.pricelist_id
        if pricelist and self.product_id and self.type != 'remove':
            price = pricelist._get_product_price(self.product_id, self.product_uom_qty, uom=self.product_uom)
            if price is False:
                warning = {
                    'title': _('No valid pricelist line found.'),
                    'message': _("Couldn't find a pricelist line matching this product and quantity.\nYou have to change either the product, the quantity or the pricelist.")
                }
                return {'warning': warning}
            else:
                self.price_unit = price
