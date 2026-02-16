from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    job_card_ids = fields.One2many(
        'job.card',
        'repair_order_id',
        string='Job Cards',
        help="Job cards linked to this repair order."
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically generate a job card for each new repair order."""
        repairs = super().create(vals_list)
        for repair in repairs:
            try:
                self.env['job.card'].create({
                    'repair_order_id': repair.id,
                })
            except Exception as e:
                _logger.warning(
                    "Failed to auto-create job card for repair order %s: %s",
                    repair.name, str(e)
                )
        return repairs
