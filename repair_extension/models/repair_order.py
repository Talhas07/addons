# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    # ===== 1.1 Customer Reference / Manual Job Card Number =====
    manual_job_card = fields.Char(
        string='Manual Job Card Number',
        copy=False,
        tracking=True,
        help="Internal manual job card reference for cross-referencing and internal tracking."
    )
    
    # ===== 1.2 Serial Number Capture =====
    appliance_serial_number = fields.Char(
        string='Appliance Serial Number',
        tracking=True,
        help="Serial number of the appliance for warranty tracking, supplier traceability, and historical records."
    )
    
    # ===== 1.3 Supplier Identification per Appliance =====
    supplier_id = fields.Many2one(
        'res.partner',
        string='Appliance Supplier',
        domain="[('is_company', '=', True)]",
        tracking=True,
        help="Supplier from which the appliance was purchased. Used for procurement, warranty claims, and reporting."
    )
    
    supplier_invoice_ref = fields.Char(
        string='Supplier Invoice Reference',
        help="Reference to the original supplier invoice for warranty claims."
    )
    
    purchase_date = fields.Date(
        string='Purchase Date',
        help="Date when the appliance was purchased from the supplier."
    )
    
    # ===== 1.4 Diagnostic Technical Report Fields =====
    fault_description = fields.Html(
        string='Fault Description',
        help="Detailed description of the fault reported by the customer."
    )
    
    diagnosis_notes = fields.Html(
        string='Diagnosis Notes',
        tracking=True,
        help="Technical diagnosis performed by the technician."
    )
    
    repair_recommendations = fields.Html(
        string='Repair Recommendations',
        help="Technician's recommendations for repair."
    )
    
    root_cause = fields.Text(
        string='Root Cause',
        help="Identified root cause of the fault."
    )
    
    diagnosis_date = fields.Datetime(
        string='Diagnosis Date',
        help="Date and time when the diagnosis was performed."
    )
    
    diagnosed_by = fields.Many2one(
        'res.users',
        string='Diagnosed By',
        help="Technician who performed the diagnosis."
    )
    
    # NOTE: Removed is_under_warranty as Odoo 18 already has 'under_warranty' field
    
    warranty_status = fields.Selection([
        ('unknown', 'Unknown'),
        ('valid', 'Valid Warranty'),
        ('expired', 'Warranty Expired'),
        ('void', 'Warranty Void'),
        ('not_applicable', 'Not Applicable'),
    ], string='Warranty Status', default='unknown', tracking=True)
    
    # Additional useful fields
    appliance_model = fields.Char(
        string='Appliance Model',
        help="Model number of the appliance."
    )
    
    appliance_brand = fields.Char(
        string='Appliance Brand',
        help="Brand of the appliance."
    )
    
    condition_on_receipt = fields.Selection([
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ], string='Condition on Receipt', default='fair')
    
    accessories_received = fields.Text(
        string='Accessories Received',
        help="List of accessories received with the appliance."
    )

    def action_set_diagnosis_date(self):
        """Set the diagnosis date and technician when diagnosis is performed."""
        self.ensure_one()
        self.write({
            'diagnosis_date': fields.Datetime.now(),
            'diagnosed_by': self.env.user.id,
        })
        return True

    def action_print_diagnostic_report(self):
        """Print the Diagnostic Technical Report."""
        self.ensure_one()
        return self.env.ref('repair_extension.action_report_diagnostic').report_action(self)

    def action_generate_diagnostic_report(self):
        """Open wizard to generate diagnostic report with options."""
        self.ensure_one()
        return {
            'name': _('Generate Diagnostic Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'repair.generate.diagnostic.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_repair_id': self.id,
            },
        }
