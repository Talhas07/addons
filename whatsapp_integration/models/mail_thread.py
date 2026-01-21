# -*- coding: utf-8 -*-

import logging

from odoo import api, models, fields
from odoo.addons.phone_validation.tools import phone_validation
from odoo.tools import html2plaintext, plaintext2html

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    message_has_whatsapp_error = fields.Boolean(
        'WhatsApp Delivery error', compute='_compute_message_has_whatsapp_error', search='_search_message_has_whatsapp_error',
        help="If checked, some messages have a delivery error.")

    def _compute_message_has_whatsapp_error(self):
        res = {}
        if self.ids:
            self._cr.execute(""" SELECT msg.res_id, COUNT(msg.res_id) FROM mail_message msg
                                 RIGHT JOIN mail_notification rel
                                 ON rel.mail_message_id = msg.id AND rel.notification_type = 'whatsapp' AND rel.notification_status in ('exception')
                                 WHERE msg.author_id = %s AND msg.model = %s AND msg.res_id in %s AND msg.message_type != 'user_notification'
                                 GROUP BY msg.res_id""",
                             (self.env.user.partner_id.id, self._name, tuple(self.ids),))
            res.update(self._cr.fetchall())

        for record in self:
            record.message_has_whatsapp_error = bool(res.get(record._origin.id, 0))

    @api.model
    def _search_message_has_whatsapp_error(self, operator, operand):
        return ['&', ('message_ids.has_whatsapp_error', operator, operand), ('message_ids.author_id', '=', self.env.user.partner_id.id)]

    def _whatsapp_get_partner_fields(self):
        fields = []
        if hasattr(self, 'partner_id'):
            fields.append('partner_id')
        if hasattr(self, 'partner_ids'):
            fields.append('partner_ids')
        return fields

    def _whatsapp_get_default_partners(self):
        partners = self.env['res.partner']
        for fname in self._whatsapp_get_partner_fields():
            partners = partners.union(*self.mapped(fname))  # ensure ordering
        return partners

    def _whatsapp_get_number_fields(self):
        if 'mobile' in self:
            return ['mobile']
        return []

    def _whatsapp_get_recipients_info(self, force_field=False, partner_fallback=True):
        result = dict.fromkeys(self.ids, False)
        tocheck_fields = [force_field] if force_field else self._whatsapp_get_number_fields()
        for record in self:
            all_numbers = [record[fname] for fname in tocheck_fields if fname in record]
            all_partners = record._whatsapp_get_default_partners()

            valid_number = False
            for fname in [f for f in tocheck_fields if f in record]:
                valid_number = phone_validation.phone_sanitize_numbers_w_record([record[fname]], record)[record[fname]]['sanitized']
                if valid_number:
                    break

            if valid_number:
                result[record.id] = {
                    'partner': all_partners[0] if all_partners else self.env['res.partner'],
                    'sanitized': valid_number,
                    'number': record[fname],
                    'partner_store': False,
                    'field_store': fname,
                }
            elif all_partners and partner_fallback:
                partner = self.env['res.partner']
                for partner in all_partners:
                    for fname in self.env['res.partner']._whatsapp_get_number_fields():
                        valid_number = phone_validation.phone_sanitize_numbers_w_record([partner[fname]], record)[partner[fname]]['sanitized']
                        if valid_number:
                            break

                if not valid_number:
                    fname = 'mobile' if partner.mobile else ('phone' if partner.phone else 'mobile')

                result[record.id] = {
                    'partner': partner,
                    'sanitized': valid_number if valid_number else False,
                    'number': partner[fname],
                    'partner_store': True,
                    'field_store': fname,
                }
            else:
                value, fname = next(
                    ((value, fname) for value, fname in zip(all_numbers, tocheck_fields) if value),
                    (False, tocheck_fields[0] if tocheck_fields else False)
                )
                result[record.id] = {
                    'partner': self.env['res.partner'],
                    'sanitized': False,
                    'number': value,
                    'partner_store': False,
                    'field_store': fname
                }
        return result

    def _message_whatsapp_schedule_mass(self, body='', template=False, active_domain=None, **composer_values):
        composer_context = {
            'default_res_model': self._name,
            'default_composition_mode': 'mass',
            'default_template_id': template.id if template else False,
        }
        if body and not template:
            composer_context['default_body'] = body
        if active_domain is not None:
            composer_context['default_use_active_domain'] = True
            composer_context['default_active_domain'] = repr(active_domain)
        else:
            composer_context['default_res_ids'] = self.ids

        create_vals = {
            'mass_force_send': False,
            'mass_keep_log': True,
        }
        if composer_values:
            create_vals.update(composer_values)

        composer = self.env['whatsapp.composer'].with_context(**composer_context).create(create_vals)
        return composer._action_send_whatsapp()

    def _message_whatsapp_with_template(self, template=False, template_xmlid=False, template_fallback='', partner_ids=False, **kwargs):
        self.ensure_one()
        if not template and template_xmlid:
            template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if template:
            body = template._render_field('body', self.ids, compute_lang=True)[self.id]
        else:
            body = self.env['whatsapp.template']._render_template(template_fallback, self._name, self.ids)[self.id]
        return self._message_whatsapp(body, partner_ids=partner_ids, **kwargs)

    def _message_whatsapp(self, body, subtype_id=False, partner_ids=False, number_field=False,
                     whatsapp_numbers=None, whatsapp_pid_to_number=None, **kwargs):
        self.ensure_one()
        whatsapp_pid_to_number = whatsapp_pid_to_number if whatsapp_pid_to_number is not None else {}

        if number_field or (partner_ids is False and whatsapp_numbers is None):
            info = self._whatsapp_get_recipients_info(force_field=number_field)[self.id]
            info_partner_ids = info['partner'].ids if info['partner'] else False
            info_number = info['sanitized'] if info['sanitized'] else info['number']
            if info_partner_ids and info_number:
                whatsapp_pid_to_number[info_partner_ids[0]] = info_number
            if info_partner_ids:
                partner_ids = info_partner_ids + (partner_ids or [])
            if not info_partner_ids:
                if info_number:
                    whatsapp_numbers = [info_number] + (whatsapp_numbers or [])
                    # will send a falsy notification allowing to fix it through WhatsApp wizards
                elif not whatsapp_numbers:
                    whatsapp_numbers = [False]

        if subtype_id is False:
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')

        return self.message_post(
            body=plaintext2html(html2plaintext(body)), partner_ids=partner_ids or [],  # TDE FIXME: temp fix otherwise crash mail_thread.py
            message_type='whatsapp', subtype_id=subtype_id,
            whatsapp_numbers=whatsapp_numbers, whatsapp_pid_to_number=whatsapp_pid_to_number,
            **kwargs
        )

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        recipients_data = super(MailThread, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        self._notify_record_by_whatsapp(message, recipients_data, msg_vals=msg_vals, **kwargs)
        return recipients_data

    def _notify_record_by_whatsapp(self, message, recipients_data, msg_vals=False,
                              whatsapp_numbers=None, whatsapp_pid_to_number=None,
                              check_existing=False, put_in_queue=False, **kwargs):
        whatsapp_pid_to_number = whatsapp_pid_to_number if whatsapp_pid_to_number is not None else {}
        whatsapp_numbers = whatsapp_numbers if whatsapp_numbers is not None else []
        whatsapp_create_vals = []
        whatsapp_all = self.env['whatsapp.msg'].sudo()

        # pre-compute WhatsApp data
        body = msg_vals['body'] if msg_vals and msg_vals.get('body') else message.body
        whatsapp_base_vals = {
            'body': html2plaintext(body),
            'mail_message_id': message.id,
            'state': 'outgoing',
        }

        # notify from computed recipients_data (followers, specific recipients)
        partners_data = [r for r in recipients_data if r['notif'] == 'whatsapp']
        partner_ids = [r['id'] for r in partners_data]
        if partner_ids:
            for partner in self.env['res.partner'].sudo().browse(partner_ids):
                number = whatsapp_pid_to_number.get(partner.id) or partner.mobile or partner.phone
                sanitize_res = phone_validation.phone_sanitize_numbers_w_record([number], partner)[number]
                number = sanitize_res['sanitized'] or number
                whatsapp_create_vals.append(dict(
                    whatsapp_base_vals,
                    partner_id=partner.id,
                    number=number
                ))

        # notify from additional numbers
        if whatsapp_numbers:
            sanitized = phone_validation.phone_sanitize_numbers_w_record(whatsapp_numbers, self)
            tocreate_numbers = [
                value['sanitized'] or original
                for original, value in sanitized.items()
            ]
            whatsapp_create_vals += [dict(
                whatsapp_base_vals,
                partner_id=False,
                number=n,
                state='outgoing' if n else 'error',
                failure_type='' if n else 'whatsapp_number_missing',
            ) for n in tocreate_numbers]

        # create whatsapp and notification
        existing_pids, existing_numbers = [], []
        if whatsapp_create_vals:
            whatsapp_all |= self.env['whatsapp.msg'].sudo().create(whatsapp_create_vals)

            if check_existing:
                existing = self.env['mail.notification'].sudo().search([
                    '|', ('res_partner_id', 'in', partner_ids),
                    '&', ('res_partner_id', '=', False), ('whatsapp_number', 'in', whatsapp_numbers),
                    ('notification_type', '=', 'whatsapp'),
                    ('mail_message_id', '=', message.id)
                ])
                for n in existing:
                    if n.res_partner_id.id in partner_ids and n.mail_message_id == message:
                        existing_pids.append(n.res_partner_id.id)
                    if not n.res_partner_id and n.whatsapp_number in whatsapp_numbers and n.mail_message_id == message:
                        existing_numbers.append(n.whatsapp_number)

            notif_create_values = [{
                'mail_message_id': message.id,
                'res_partner_id': whatsapp.partner_id.id,
                'whatsapp_number': whatsapp.number,
                'notification_type': 'whatsapp',
                'whatsapp_id': whatsapp.id,
                'is_read': True,  # discard Inbox notification
                'notification_status': 'ready' if whatsapp.state == 'outgoing' else 'exception',
                'failure_type': '' if whatsapp.state == 'outgoing' else whatsapp.failure_type,
            } for whatsapp in whatsapp_all if (whatsapp.partner_id and whatsapp.partner_id.id not in existing_pids) or (not whatsapp.partner_id and whatsapp.number not in existing_numbers)]
            if notif_create_values:
                self.env['mail.notification'].sudo().create(notif_create_values)

            if existing_pids or existing_numbers:
                for whatsapp in whatsapp_all:
                    notif = next((n for n in existing if
                                 (n.res_partner_id.id in existing_pids and n.res_partner_id.id == whatsapp.partner_id.id) or
                                 (not n.res_partner_id and n.whatsapp_number in existing_numbers and n.whatsapp_number == whatsapp.number)), False)
                    if notif:
                        notif.write({
                            'notification_type': 'whatsapp',
                            'notification_status': 'ready',
                            'whatsapp_id': whatsapp.id,
                            'whatsapp_number': whatsapp.number,
                        })

        if whatsapp_all and not put_in_queue:
            whatsapp_all.filtered(lambda whatsapp: whatsapp.state == 'outgoing').send(auto_commit=False, raise_exception=False)

        return True
