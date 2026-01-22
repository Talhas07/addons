# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class RepairGenerateDiagnosticReport(models.TransientModel):
    _name = 'repair.generate.diagnostic.report'
    _description = 'Generate Diagnostic Report Wizard'

    repair_id = fields.Many2one(
        'repair.order',
        string='Repair Order',
        required=True,
        readonly=True,
    )
    
    include_internal_notes = fields.Boolean(
        string='Include Internal Notes',
        default=False,
        help="Include internal notes in the report (for internal use only)."
    )
    
    include_pricing = fields.Boolean(
        string='Include Pricing',
        default=True,
        help="Include pricing information in the report."
    )
    
    set_diagnosis_date = fields.Boolean(
        string='Set Diagnosis Date Now',
        default=True,
        help="Automatically set the diagnosis date to current time if not already set."
    )
    
    diagnosed_by = fields.Many2one(
        'res.users',
        string='Diagnosed By',
        default=lambda self: self.env.user,
        help="Technician who performed the diagnosis."
    )

    @api.onchange('repair_id')
    def _onchange_repair_id(self):
        if self.repair_id and self.repair_id.diagnosed_by:
            self.diagnosed_by = self.repair_id.diagnosed_by

    def action_print_report(self):
        """Generate and print the diagnostic report."""
        self.ensure_one()
        
        # Update diagnosis info if requested
        if self.set_diagnosis_date and not self.repair_id.diagnosis_date:
            self.repair_id.write({
                'diagnosis_date': fields.Datetime.now(),
                'diagnosed_by': self.diagnosed_by.id,
            })
        elif self.diagnosed_by and self.diagnosed_by != self.repair_id.diagnosed_by:
            self.repair_id.write({
                'diagnosed_by': self.diagnosed_by.id,
            })
        
        # Generate the report
        return self.env.ref('repair_extension.action_report_diagnostic').report_action(self.repair_id)

    def action_send_by_email(self):
        """Send the diagnostic report by email."""
        self.ensure_one()
        
        # Update diagnosis info if requested
        if self.set_diagnosis_date and not self.repair_id.diagnosis_date:
            self.repair_id.write({
                'diagnosis_date': fields.Datetime.now(),
                'diagnosed_by': self.diagnosed_by.id,
            })
        
        # Open email composer with the report attached
        template = self.env.ref('repair_extension.mail_template_diagnostic_report', raise_if_not_found=False)
        
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=False)
        ctx = {
            'default_model': 'repair.order',
            'default_res_ids': [self.repair_id.id],
            'default_use_template': bool(template),
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'force_email': True,
        }
        
        return {
            'name': _('Send Diagnostic Report'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
