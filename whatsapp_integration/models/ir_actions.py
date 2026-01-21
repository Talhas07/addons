# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ServerActions(models.Model):
    """ Add WhatsApp option in server actions. """
    _name = 'ir.actions.server'
    _inherit = ['ir.actions.server']

    state = fields.Selection(selection_add=[
        ('whatsapp', 'Send WhatsApp Text Message'),
    ], ondelete={'whatsapp': 'cascade'})
    # WhatsApp
    whatsapp_template_id = fields.Many2one(
        'whatsapp.template', 'WhatsApp Template', ondelete='set null',
        domain="[('model_id', '=', model_id)]",
    )
    whatsapp_mass_keep_log = fields.Boolean('WhatsApp Log as Note', default=True)

    @api.constrains('state', 'model_id')
    def _check_whatsapp_capability(self):
        for action in self:
            if action.state == 'whatsapp' and not action.model_id.is_mail_thread:
                raise ValidationError(_("Sending WhatsApp can only be done on a mail.thread model"))

    def _run_action_whatsapp_multi(self, eval_context=None):
        if not self.whatsapp_template_id or self._is_recompute():
            return False

        records = eval_context.get('records') or eval_context.get('record')
        if not records:
            return False
        partner_ids = []    
        if records._name == 'res.partner':  
            partner_ids = records.mapped('id')  
        else:   
            partner_ids = records.mapped('partner_id')  
        composer = self.env['whatsapp.msg'].with_context(
            default_res_model=records._name,
            default_res_ids=records.ids,
            default_res_id=records.ids[0],
            default_template_id=self.whatsapp_template_id.id,
            default_parnter_ids=partner_ids,
        ).create({})
        composer._compute_message()
        composer.action_send_msg()
        return False
