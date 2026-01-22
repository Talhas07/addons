# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class RepairFee(models.Model):
    """Repair Fees model - legacy v16 compatibility"""
    _name = 'repair.fee'
    _description = 'Repair Fees'

    repair_id = fields.Many2one(
        'repair.order', 'Repair Order Reference',
        index=True, ondelete='cascade', required=True)
    company_id = fields.Many2one(
        related="repair_id.company_id", index=True, store=True)
    currency_id = fields.Many2one(
        related="repair_id.currency_id")
    name = fields.Text('Description', index=True, required=True)
    product_id = fields.Many2one(
        'product.product', 'Product', check_company=True,
        domain="[('type', '=', 'service'), '|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    product_uom_qty = fields.Float(
        'Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price')
    product_uom = fields.Many2one(
        'uom.uom', 'Product Unit of Measure', required=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    price_subtotal = fields.Float(
        'Subtotal', compute='_compute_price_total_and_subtotal', store=True, digits=0)
    price_total = fields.Float(
        'Total', compute='_compute_price_total_and_subtotal', store=True, digits=0)
    tax_id = fields.Many2many(
        'account.tax', 'repair_fee_line_tax', 'repair_fee_line_id', 'tax_id', 'Taxes',
        domain="[('type_tax_use','=','sale'), ('company_id', '=', company_id)]", check_company=True)
    invoice_line_id = fields.Many2one(
        'account.move.line', 'Invoice Line', copy=False, readonly=True, check_company=True)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)

    @api.depends('price_unit', 'repair_id', 'product_uom_qty', 'product_id', 'tax_id')
    def _compute_price_total_and_subtotal(self):
        for fee in self:
            currency = fee.repair_id.pricelist_id.currency_id if fee.repair_id.pricelist_id else self.env.company.currency_id
            taxes = fee.tax_id.compute_all(
                fee.price_unit, currency, fee.product_uom_qty,
                fee.product_id, fee.repair_id.partner_id)
            fee.price_subtotal = taxes['total_excluded']
            fee.price_total = taxes['total_included']

    @api.onchange('repair_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """On change of product it sets product quantity, tax account, name, uom of product, unit price and price subtotal."""
        if not self.product_id:
            return

        self = self.with_company(self.company_id)

        partner = self.repair_id.partner_id
        partner_invoice = self.repair_id.partner_invoice_id or partner
        pricelist = self.repair_id.pricelist_id

        if partner and self.product_id:
            fpos = self.env['account.fiscal.position']._get_fiscal_position(
                partner_invoice, delivery=self.repair_id.partner_id)
            taxes = self.product_id.taxes_id.filtered(lambda x: x.company_id == self.repair_id.company_id)
            self.tax_id = fpos.map_tax(taxes)
        if partner:
            self.name = self.product_id.with_context(lang=partner.lang).display_name
        else:
            self.name = self.product_id.display_name
        self.product_uom = self.product_id.uom_id.id
        if self.product_id.description_sale:
            if partner:
                self.name += '\n' + self.product_id.with_context(lang=partner.lang).description_sale
            else:
                self.name += '\n' + self.product_id.description_sale

        warning = False
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
        if pricelist and self.product_id:
            price = pricelist._get_product_price(self.product_id, self.product_uom_qty, uom=self.product_uom)
            if price is False:
                warning = {
                    'title': _('No valid pricelist line found.'),
                    'message': _("Couldn't find a pricelist line matching this product and quantity.\nYou have to change either the product, the quantity or the pricelist.")
                }
                return {'warning': warning}
            else:
                self.price_unit = price

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('product_uom'):
                vals['product_uom'] = self.env["product.product"].browse(vals.get('product_id')).uom_id.id
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('product_id') and not vals.get('product_uom'):
            vals['product_uom'] = self.env["product.product"].browse(vals.get('product_id')).uom_id.id
        return super().write(vals)
