from odoo import models, fields, api
from datetime import datetime

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
        # Automatically populate fields from linked repair order
        # Ensure the job card reference is set from the sequence when not provided
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('job.card')
        if vals.get('repair_order_id'):
            repair_order = self.env['repair.order'].browse(vals['repair_order_id'])
            vals.update({
                'product_id': repair_order.product_id.id,
                'description': repair_order.description,
                'customer_reference': repair_order.client_order_ref,
                'technician_id': repair_order.assigned_technician_id.id,
            })
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
                    raise ValueError("You cannot edit Diagnosis Notes or Images after they are submitted.")

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
