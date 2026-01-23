# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = 'repair.order'
    
    # ===== Amount Fields (if not in Odoo 18) =====
    # These provide the totals section like in Odoo 16
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    amount_tax = fields.Monetary(
        string='Taxes',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
    )
    
    # Currency field for monetary fields
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        store=True,
    )
    
    @api.depends('company_id')
    def _compute_currency_id(self):
        for repair in self:
            repair.currency_id = repair.company_id.currency_id or self.env.company.currency_id
    
    @api.depends('move_ids', 'move_ids.state', 'move_ids.product_id', 'move_ids.product_uom_qty')
    def _compute_amounts(self):
        """Compute the total amounts for the repair order."""
        for repair in self:
            amount_untaxed = 0.0
            amount_tax = 0.0
            
            # Try to get amounts from parts/operations if they exist
            # This handles different Odoo 18 structures
            
            # Check if 'operations' field exists (Odoo 16 style)
            if hasattr(repair, 'operations') and repair.operations:
                for line in repair.operations:
                    if hasattr(line, 'price_subtotal'):
                        amount_untaxed += line.price_subtotal
                    if hasattr(line, 'price_total') and hasattr(line, 'price_subtotal'):
                        amount_tax += (line.price_total - line.price_subtotal)
            
            # Check if 'fees_lines' field exists (Odoo 16 style)
            if hasattr(repair, 'fees_lines') and repair.fees_lines:
                for line in repair.fees_lines:
                    if hasattr(line, 'price_subtotal'):
                        amount_untaxed += line.price_subtotal
                    if hasattr(line, 'price_total') and hasattr(line, 'price_subtotal'):
                        amount_tax += (line.price_total - line.price_subtotal)
            
            # Check if 'parts_lines' exists (possible Odoo 18 structure)
            if hasattr(repair, 'parts_lines') and repair.parts_lines:
                for line in repair.parts_lines:
                    if hasattr(line, 'price_subtotal'):
                        amount_untaxed += line.price_subtotal
                    if hasattr(line, 'price_total') and hasattr(line, 'price_subtotal'):
                        amount_tax += (line.price_total - line.price_subtotal)
            
            repair.amount_untaxed = amount_untaxed
            repair.amount_tax = amount_tax
            repair.amount_total = amount_untaxed + amount_tax

    # ===== 1.1 Customer Reference / Job Card ID =====
    job_card_id = fields.Integer(
        string='Job Card ID',
        copy=False,
        tracking=True,
        help="Internal job card ID for cross-referencing and internal tracking."
    )
    
    customer_reference = fields.Char(
        string='Customer Reference',
        tracking=True,
        help="Customer's own reference number for this repair."
    )
    
    # ===== Description =====
    description = fields.Char(
        string='Description',
        help="Detailed description of the repair work to be done."
    )
    
    # ===== Product Barcode =====
    product_bar_code = fields.Char(
        string='Product Barcode',
        store=True,
        help="Barcode of the product being repaired."
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
    
    # ===== Assigned Technician =====
    assigned_technician_id = fields.Many2one(
        'res.users',
        string='Assigned Technician',
        tracking=True,
        help="Technician assigned to perform the repair."
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
