# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import float_compare, is_html_empty
from collections import defaultdict

import logging
_logger = logging.getLogger(__name__)


class Repair(models.Model):
    _inherit = "repair.order"
    _order = "schedule_date desc"

    product_bar_code = fields.Char(string="Barcode for Product to Repair")
    customer_reference = fields.Char(string="Customer Reference")
    supplier_id = fields.Many2one('res.partner', 'Supplier', copy=False, tracking=True)
    diagnostic_invoice_id = fields.Many2one(
        'account.move', 'Diagnostic Invoice',
        copy=False, readonly=True, tracking=True,
        domain=[('move_type', '=', 'out_invoice')])
    invoiced = fields.Boolean(
        string='Invoiced',
        copy=False,
        default=False,
        help="Indicates whether a repair invoice has been created")


    def action_repair_invoice_create_2(self):
        for repair in self:
            _logger.info("A action_repair_invoice_create 1")
            # Note: invoice_method field may not exist in Odoo 18
            # repair.invoice_method = "after_repair"
            _logger.info("B action_repair_invoice_create 2")
            #repair._create_invoices()   
            group=False
            grouped_invoices_vals = {}         
            repair = repair.with_company(repair.company_id)
            partner_invoice = repair.partner_invoice_id or repair.partner_id
            if not partner_invoice:
                raise UserError(_('You have to select an invoice address in the repair form.'))

            narration = repair.quotation_notes
            currency = repair.pricelist_id.currency_id
            company = repair.env.company

            if (partner_invoice.id, currency.id, company.id) not in grouped_invoices_vals:
                grouped_invoices_vals[(partner_invoice.id, currency.id, company.id)] = []
            current_invoices_list = grouped_invoices_vals[(partner_invoice.id, currency.id, company.id)]

            
            fpos = self.env['account.fiscal.position']._get_fiscal_position(partner_invoice, delivery=repair.address_id)
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': partner_invoice.id,
                'partner_shipping_id': repair.address_id.id,
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
            
            # Create invoice lines from operations.
            for operation in repair.operations.filtered(lambda op: op.type == "add"):
                if "DIAGNOSIS" in operation.name.upper():
                    continue
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

                if currency == company.currency_id:
                    balance = -(operation.product_uom_qty * operation.price_unit)
                    invoice_line_vals.update({
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                    })
                else:
                    amount_currency = -(operation.product_uom_qty * operation.price_unit)
                    balance = currency._convert(amount_currency, company.currency_id, company, fields.Date.today())
                    invoice_line_vals.update({
                        'amount_currency': amount_currency,
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                        'currency_id': currency.id,
                    })
                invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

            # Create invoice lines from fees.
            for fee in repair.fees_lines:
                if "DIAGNOSIS" in fee.name.upper():
                    continue
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

                if currency == company.currency_id:
                    balance = -(fee.product_uom_qty * fee.price_unit)
                    invoice_line_vals.update({
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                    })
                else:
                    amount_currency = -(fee.product_uom_qty * fee.price_unit)
                    balance = currency._convert(amount_currency, company.currency_id, company,
                                                fields.Date.today())
                    invoice_line_vals.update({
                        'amount_currency': amount_currency,
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                        'currency_id': currency.id,
                    })
                invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

            # Create invoices.
            invoices_vals_list_per_company = defaultdict(list)
            for (partner_invoice_id, currency_id, company_id), invoices in grouped_invoices_vals.items():
                for invoice in invoices:
                    invoices_vals_list_per_company[company_id].append(invoice)

            for company_id, invoices_vals_list in invoices_vals_list_per_company.items():
                # VFE TODO remove the default_company_id ctxt key ?
                # Account fallbacks on self.env.company, which is correct with with_company
                self.env['account.move'].with_company(company_id).with_context(default_company_id=company_id, default_move_type='out_invoice').create(invoices_vals_list)

            repair.write({'invoiced': True})
            # repairs.mapped('operations').filtered(lambda op: op.type == 'add').write({'invoiced': True})
            # repairs.mapped('fees_lines').write({'invoiced': True})

            # return dict((repair.id, repair.invoice_id.id) for repair in repairs)

            _logger.info("C action_repair_invoice_create 3")

    def create_dignostic_invoice(self):
        fpos = self.env['account.fiscal.position']._get_fiscal_position(self.partner_id, delivery=self.address_id)
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.address_id.id,
            'currency_id': self.env.company.currency_id.id,
            'narration': "Diagnostic Invoice",
            'invoice_origin': self.name,
            'repair_ids': [(4, self.id)],
            'invoice_line_ids': [],
            'fiscal_position_id': fpos.id
        }
        invoice_line_vals = {
                    'name': "Diagnosing the issue",                    
                    'quantity': 1,
                    'price_unit': 200,
                }

        invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

        inv = self.env['account.move'].with_company(self.env.company).with_context(default_company_id=self.env.company, default_move_type='out_invoice').create(invoice_vals)
        
        self.ensure_one()
        self.diagnostic_invoice_id = inv.id      

        return {
            'name': _('Invoice created'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
            'res_id': inv.id,
            }