# -*- coding: utf-8 -*-

from odoo import api, fields, models


class IrModel(models.Model):
    _inherit = 'ir.model'

    is_mail_thread_whatsapp = fields.Boolean(
        string="Mail Thread WhatsApp", default=False,
        store=False, compute='_compute_is_mail_thread_whatsapp', search='_search_is_mail_thread_whatsapp',
        help="Whether this model supports messages and notifications through WhatsApp",
    )

    @api.depends('is_mail_thread')
    def _compute_is_mail_thread_whatsapp(self):
        for model in self:
            if model.is_mail_thread:
                ModelObject = self.env[model.model]
                potential_fields = ModelObject._whatsapp_get_number_fields() + ModelObject._whatsapp_get_partner_fields()
                if any(fname in ModelObject._fields for fname in potential_fields):
                    model.is_mail_thread_whatsapp = True
                    continue
            model.is_mail_thread_whatsapp = False

    def _search_is_mail_thread_whatsapp(self, operator, value):
        thread_models = self.search([('is_mail_thread', '=', True)])
        valid_models = self.env['ir.model']
        for model in thread_models:
            if model.model not in self.env:
                continue
            ModelObject = self.env[model.model]
            potential_fields = ModelObject._whatsapp_get_number_fields() + ModelObject._whatsapp_get_partner_fields()
            if any(fname in ModelObject._fields for fname in potential_fields):
                valid_models |= model

        search_whatsapp = (operator == '=' and value) or (operator == '!=' and not value)
        if search_whatsapp:
            return [('id', 'in', valid_models.ids)]
        return [('id', 'not in', valid_models.ids)]
