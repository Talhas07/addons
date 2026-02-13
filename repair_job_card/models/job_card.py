from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)


class JobCard(models.Model):
    _name = "job.card"
    _description = "Job Card"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string="Job Card Reference", 
        required=True, 
        copy=False, 
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('job.card')
    )
    repair_order_id = fields.Many2one(
        "repair.order", 
        string="Repair Order", 
        required=False, 
        readonly=True, 
        ondelete='set null',
        help="The repair order linked to this job card."
    ) 
    product_bar_code = fields.Char(
        string="Product Barcode",
        help="Barcode of the product being repaired."
    )
   
    technician_id = fields.Many2one(
        "res.users", 
        string="Technician", 
        required=False, 
        default=lambda self: self.env.uid,
        help="Assigned technician for this job card."
    )
    product_id = fields.Many2one(
        "product.product", 
        string="Product", 
        readonly=True, 
        help="Product being repaired (linked from repair order)."
    )
    description = fields.Text(
        string="Job Description", 
        help="Description of the repair task."
    )
    customer_reference = fields.Char(
        string="Customer Reference", 
        readonly=True, 
        help="Customer-provided reference number for the repair."
    )

    # Diagnosis Section
    diagnosis_notes = fields.Text(
        string="Diagnosis Notes", 
        help="Technician's diagnosis details. Can only be added once."
    )
    diagnosis_images = fields.Binary(
        string="Diagnosis Images", 
        help="Upload images of faulty components."
    )
    diagnosis_submitted = fields.Boolean(
        string="Diagnosis Submitted", 
        default=False, 
        readonly=True, 
        help="Indicates if the diagnosis has been submitted."
    )

    # Status and Timestamps
    status = fields.Selection(
        [
            ('assigned', 'Assigned'),
            ('under_repair', 'Under Repair'),
            ('waiting_parts', 'Waiting for Parts'),
            ('complete', 'Complete'),
            ('closed', 'Closed'),
            ('confirmed', 'Confirmed'),
        ],
        string="Status", 
        default="assigned", 
        tracking=True, 
        help="Status of the repair job."
    )
    date_assigned = fields.Datetime(
        string="Assigned Date", 
        default=lambda self: datetime.now(), 
        readonly=True
    )
    date_started = fields.Datetime(
        string="Start Date", 
        readonly=True
    )
    date_completed = fields.Datetime(
        string="Completion Date", 
        readonly=True
    )

    # Archiving Support
    active = fields.Boolean(
        string="Active", 
        default=True,
        help="Set to False to archive the job card without deleting it."
    )

    # Overrides
    @api.model
    def create(self, vals):
        # Ensure the job card reference is set from the sequence when not provided
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('job.card')

        # Automatically populate fields from linked repair order
        if vals.get('repair_order_id'):
            repair_order = self.env['repair.order'].browse(vals['repair_order_id'])
            if repair_order.exists():
                update_vals = {
                    'product_id': repair_order.product_id.id if repair_order.product_id else False,
                }

                # Customer Reference (from repair_extension / cord_len)
                if hasattr(repair_order, 'customer_reference') and repair_order.customer_reference:
                    update_vals['customer_reference'] = repair_order.customer_reference

                # Product Barcode - try product_bar_code (cord_len) first, then product_barcode (repair_extension)
                if hasattr(repair_order, 'product_bar_code') and repair_order.product_bar_code:
                    update_vals['product_bar_code'] = repair_order.product_bar_code
                elif hasattr(repair_order, 'product_barcode') and repair_order.product_barcode:
                    update_vals['product_bar_code'] = repair_order.product_barcode
                elif repair_order.product_id and repair_order.product_id.barcode:
                    update_vals['product_bar_code'] = repair_order.product_id.barcode

                # Technician (from repair_extension)
                if hasattr(repair_order, 'technician_id') and repair_order.technician_id:
                    update_vals['technician_id'] = repair_order.technician_id.id

                # Description - try repair_description (repair_extension) first, then internal_notes
                if hasattr(repair_order, 'repair_description') and repair_order.repair_description:
                    update_vals['description'] = repair_order.repair_description
                elif hasattr(repair_order, 'internal_notes') and repair_order.internal_notes:
                    update_vals['description'] = repair_order.internal_notes

                vals.update(update_vals)

        return super(JobCard, self).create(vals)

    def write(self, vals):
        # Handle timestamps for status changes
        if vals.get('status') == 'under_repair' and not self.date_started:
            vals['date_started'] = datetime.now()
        if vals.get('status') == 'complete' and not self.date_completed:
            vals['date_completed'] = datetime.now()

        # Prevent edits to Diagnosis Notes after submission
        if 'diagnosis_notes' in vals or 'diagnosis_images' in vals:
            for record in self:
                if record.diagnosis_submitted:
                    raise UserError("You cannot edit Diagnosis Notes or Images after they are submitted.")
            # Mark diagnosis as submitted
            vals['diagnosis_submitted'] = True

        return super(JobCard, self).write(vals)

    def action_update_status(self, new_status):
        """Update status of job card and reflect changes in corresponding repair order."""
        self.ensure_one()
        if new_status in dict(self._fields['status'].selection):
            self.status = new_status
            if self.repair_order_id:
                self.repair_order_id.write({'state': new_status})

    @api.model
    def _cron_create_job_cards(self):
        """Cron job: Automatically create job cards for repair orders that don't have one yet."""
        # Find all repair order IDs that already have a job card
        existing_repair_ids = self.search([
            ('repair_order_id', '!=', False)
        ]).mapped('repair_order_id').ids

        # Find repair orders that are confirmed/in-progress but have no job card
        # Standard Odoo 18 repair states: draft, confirmed, under_repair, ready, done, cancel
        repair_orders = self.env['repair.order'].search([
            ('id', 'not in', existing_repair_ids),
            ('state', 'in', ['confirmed', 'under_repair', 'ready']),
        ])

        created_count = 0
        for repair in repair_orders:
            try:
                self.create({
                    'repair_order_id': repair.id,
                })
                created_count += 1
            except Exception as e:
                _logger.warning(
                    "Failed to create job card for repair order %s: %s",
                    repair.name, str(e)
                )

        if created_count:
            _logger.info(
                "Cron: Created %d job card(s) from repair orders.", created_count
            )
        return True
