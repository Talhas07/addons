# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, is_html_empty


class RepairOrder(models.Model):
    """Extends repair.order with legacy v16 fields for invoice and pricelist support"""
    _inherit = 'repair.order'

    # Legacy Invoice Fields
    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist',
        default=lambda self: self.env['product.pricelist'].search(
            [('company_id', 'in', [self.env.company.id, False])], limit=1).id,
        help='Pricelist of the selected partner.', check_company=True)
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        compute='_compute_currency_id', store=True, readonly=False)
    partner_invoice_id = fields.Many2one(
        'res.partner', 'Invoicing Address', check_company=True)
    invoice_method = fields.Selection([
        ("none", "No Invoice"),
        ("b4repair", "Before Repair"),
        ("after_repair", "After Repair")], string="Invoice Method",
        default='none', index=True, required=True,
        help='Selecting \'Before Repair\' or \'After Repair\' will allow you to generate invoice before or after the repair is done respectively. \'No invoice\' means you don\'t want to generate invoice for this repair order.')
    invoice_id = fields.Many2one(
        'account.move', 'Invoice',
        copy=False, readonly=True, tracking=True,
        domain=[('move_type', '=', 'out_invoice')])
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    invoice_state = fields.Selection(
        string='Invoice State', related='invoice_id.state')

    # Legacy Parts and Fees
    operations = fields.One2many(
        'repair.line', 'repair_id', 'Parts',
        copy=True)
    fees_lines = fields.One2many(
        'repair.fee', 'repair_id', 'Operations',
        copy=True)

    # Legacy Warranty Field
    guarantee_limit = fields.Date('Warranty Expiration')

    # Legacy Description Field
    description = fields.Char('Repair Description')

    # Legacy Quotation Notes
    quotation_notes = fields.Html('Quotation Notes')

    # Product Barcode (computed from product)
    product_bar_code = fields.Char(
        'Product Barcode', related='product_id.barcode',
        readonly=True, store=False)

    # Legacy Amount Fields
    amount_untaxed = fields.Float(
        'Untaxed Amount', compute='_compute_amount_untaxed', store=True)
    amount_tax = fields.Float(
        'Taxes', compute='_compute_amount_tax', store=True)
    amount_total = fields.Float(
        'Total', compute='_compute_amount_total', store=True)

    # Legacy repaired field
    repaired = fields.Boolean('Repaired', copy=False, readonly=True)

    @api.depends('pricelist_id', 'pricelist_id.currency_id')
    def _compute_currency_id(self):
        for order in self:
            order.currency_id = order.pricelist_id.currency_id or self.env.company.currency_id

    @api.depends('operations.price_subtotal', 'fees_lines.price_subtotal', 'pricelist_id.currency_id')
    def _compute_amount_untaxed(self):
        for order in self:
            total = sum(operation.price_subtotal for operation in order.operations)
            total += sum(fee.price_subtotal for fee in order.fees_lines)
            currency = order.pricelist_id.currency_id or self.env.company.currency_id
            order.amount_untaxed = currency.round(total) if currency else total

    @api.depends('operations.price_unit', 'operations.product_uom_qty', 'operations.product_id',
                 'fees_lines.price_unit', 'fees_lines.product_uom_qty', 'fees_lines.product_id',
                 'pricelist_id.currency_id', 'partner_id')
    def _compute_amount_tax(self):
        for order in self:
            val = 0.0
            currency = order.pricelist_id.currency_id or self.env.company.currency_id
            for operation in order.operations:
                if operation.tax_id:
                    tax_calculate = operation.tax_id.compute_all(
                        operation.price_unit, currency, operation.product_uom_qty,
                        operation.product_id, order.partner_id)
                    for c in tax_calculate['taxes']:
                        val += c['amount']
            for fee in order.fees_lines:
                if fee.tax_id:
                    tax_calculate = fee.tax_id.compute_all(
                        fee.price_unit, currency, fee.product_uom_qty,
                        fee.product_id, order.partner_id)
                    for c in tax_calculate['taxes']:
                        val += c['amount']
            order.amount_tax = val

    @api.depends('amount_untaxed', 'amount_tax')
    def _compute_amount_total(self):
        for order in self:
            currency = order.pricelist_id.currency_id or self.env.company.currency_id
            order.amount_total = currency.round(order.amount_untaxed + order.amount_tax) if currency else (order.amount_untaxed + order.amount_tax)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """Update addresses and pricelist based on partner"""
        self = self.with_company(self.company_id)
        if not self.partner_id:
            self.partner_invoice_id = False
            self.pricelist_id = self.env['product.pricelist'].search([
                ('company_id', 'in', [self.env.company.id, False]),
            ], limit=1)
        else:
            addresses = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
            self.partner_invoice_id = addresses['invoice']
            if self.partner_id.property_product_pricelist:
                self.pricelist_id = self.partner_id.property_product_pricelist.id

    def action_repair_invoice_create(self):
        """Create invoices for repair orders"""
        for repair in self:
            repair._create_invoices()
            if repair.invoice_method == 'b4repair':
                repair.write({'state': 'confirmed'})
            elif repair.invoice_method == 'after_repair':
                repair.write({'state': 'done'})
        return True

    def _create_invoices(self, group=False):
        """Creates invoice(s) for repair order."""
        grouped_invoices_vals = {}
        repairs = self.filtered(lambda repair: repair.state not in ('draft', 'cancel')
                                               and not repair.invoice_id
                                               and repair.invoice_method != 'none')
        for repair in repairs:
            repair = repair.with_company(repair.company_id)
            partner_invoice = repair.partner_invoice_id or repair.partner_id
            if not partner_invoice:
                raise UserError(_('You have to select an invoice address in the repair form.'))

            narration = repair.quotation_notes
            currency = repair.pricelist_id.currency_id or self.env.company.currency_id
            company = repair.env.company

            if (partner_invoice.id, currency.id, company.id) not in grouped_invoices_vals:
                grouped_invoices_vals[(partner_invoice.id, currency.id, company.id)] = []
            current_invoices_list = grouped_invoices_vals[(partner_invoice.id, currency.id, company.id)]

            if not group or len(current_invoices_list) == 0:
                fpos = self.env['account.fiscal.position']._get_fiscal_position(
                    partner_invoice, delivery=repair.partner_id)
                invoice_vals = {
                    'move_type': 'out_invoice',
                    'partner_id': partner_invoice.id,
                    'currency_id': currency.id,
                    'narration': narration if not is_html_empty(narration) else '',
                    'invoice_origin': repair.name,
                    'repair_ids': [(4, repair.id)],
                    'invoice_line_ids': [],
                    'fiscal_position_id': fpos.id
                }
                if partner_invoice.property_payment_term_id:
                    invoice_vals['invoice_payment_term_id'] = partner_invoice.property_payment_term_id.id
                current_invoices_list.append(invoice_vals)
            else:
                invoice_vals = current_invoices_list[0]
                invoice_vals['invoice_origin'] += ', ' + repair.name
                invoice_vals['repair_ids'].append((4, repair.id))
                if not is_html_empty(narration):
                    if is_html_empty(invoice_vals['narration']):
                        invoice_vals['narration'] = narration
                    else:
                        invoice_vals['narration'] += Markup('<br/>') + narration

            # Create invoice lines from operations
            for operation in repair.operations.filtered(lambda op: op.type == 'add'):
                if group:
                    name = repair.name + '-' + operation.name
                else:
                    name = operation.name

                account = operation.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)['income']
                if not account:
                    raise UserError(_('No account defined for product "%s".', operation.product_id.name))

                invoice_line_vals = {
                    'name': name,
                    'account_id': account.id,
                    'quantity': operation.product_uom_qty,
                    'tax_ids': [(6, 0, operation.tax_id.ids)],
                    'product_uom_id': operation.product_uom.id,
                    'price_unit': operation.price_unit,
                    'product_id': operation.product_id.id,
                    'repair_line_ids': [(4, operation.id)],
                }
                invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

            # Create invoice lines from fees
            for fee in repair.fees_lines:
                if group:
                    name = repair.name + '-' + fee.name
                else:
                    name = fee.name

                if not fee.product_id:
                    raise UserError(_('No product defined on fees.'))

                account = fee.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fpos)['income']
                if not account:
                    raise UserError(_('No account defined for product "%s".', fee.product_id.name))

                invoice_line_vals = {
                    'name': name,
                    'account_id': account.id,
                    'quantity': fee.product_uom_qty,
                    'tax_ids': [(6, 0, fee.tax_id.ids)],
                    'product_uom_id': fee.product_uom.id,
                    'price_unit': fee.price_unit,
                    'product_id': fee.product_id.id,
                    'repair_fee_ids': [(4, fee.id)],
                }
                invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

        # Create invoices
        invoices_vals_list_per_company = defaultdict(list)
        for (partner_invoice_id, currency_id, company_id), invoices in grouped_invoices_vals.items():
            for invoice in invoices:
                invoices_vals_list_per_company[company_id].append(invoice)

        for company_id, invoices_vals_list in invoices_vals_list_per_company.items():
            self.env['account.move'].with_company(company_id).with_context(
                default_company_id=company_id, default_move_type='out_invoice').create(invoices_vals_list)

        repairs.write({'invoiced': True})
        repairs.mapped('operations').filtered(lambda op: op.type == 'add').write({'invoiced': True})
        repairs.mapped('fees_lines').write({'invoiced': True})

        return dict((repair.id, repair.invoice_id.id) for repair in repairs)

    def action_created_invoice(self):
        """View created invoice"""
        self.ensure_one()
        return {
            'name': _('Invoice created'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
            'res_id': self.invoice_id.id,
        }

    def print_repair_order(self):
        """Print repair order report"""
        return self.env.ref('repair_custom.action_report_repair_order').report_action(self)
