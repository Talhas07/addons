# -*- coding: utf-8 -*-

from odoo import api, fields, models


class WhatsAppTemplatePreview(models.TransientModel):
    _name = "whatsapp.template.preview"
    _description = "WhatsApp Template Preview"

    @api.model
    def _selection_target_model(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]

    @api.model
    def _selection_languages(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def default_get(self, fields):
        result = super(WhatsAppTemplatePreview, self).default_get(fields)
        whatsapp_template_id = self.env.context.get('default_whatsapp_template_id')
        if not whatsapp_template_id or 'resource_ref' not in fields:
            return result
        whatsapp_template = self.env['whatsapp.template'].browse(whatsapp_template_id)
        res = self.env[whatsapp_template.model_id.model].search([], limit=1)
        if res:
            result['resource_ref'] = '%s,%s' % (whatsapp_template.model_id.model, res.id)
        return result

    whatsapp_template_id = fields.Many2one('whatsapp.template', required=True, ondelete='cascade')
    lang = fields.Selection(_selection_languages, string='Template Preview Language')
    model_id = fields.Many2one('ir.model', related="whatsapp_template_id.model_id")
    body = fields.Text('Body', compute='_compute_whatsapp_template_fields')
    resource_ref = fields.Reference(string='Record reference', selection='_selection_target_model')
    no_record = fields.Boolean('No Record', compute='_compute_no_record')

    @api.depends('model_id')
    def _compute_no_record(self):
        for preview in self:
            preview.no_record = (self.env[preview.model_id.model].search_count([]) == 0) if preview.model_id else True

    @api.depends('lang', 'resource_ref')
    def _compute_whatsapp_template_fields(self):
        for wizard in self:
            if wizard.whatsapp_template_id and wizard.resource_ref:
                wizard.body = wizard.whatsapp_template_id._render_field('body', [wizard.resource_ref.id], set_lang=wizard.lang)[wizard.resource_ref.id]
            else:
                wizard.body = wizard.whatsapp_template_id.body
