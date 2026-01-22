# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class RepairMakeInvoice(models.TransientModel):
    _name = 'repair.make.invoice'
    _description = 'Create Invoices for Repairs'

    group = fields.Boolean('Group by partner invoice address')

    def make_invoices(self):
        repairs = self.env['repair.order'].browse(self._context.get('active_ids', []))
        repairs._create_invoices(group=self.group)
        return {'type': 'ir.actions.act_window_close'}
