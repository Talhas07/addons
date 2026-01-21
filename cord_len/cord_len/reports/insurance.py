# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2017 AP Accounting (www.ap-accounting.co.za) All rights reserved.
#    Billiard Made bill@fintechfundi.com
#
##############################################################################


from odoo import models, fields, api, exceptions, _
from datetime import datetime

class RptInsurance(models.TransientModel):
    _name = "rpt.insurance"
    _description = 'Qweb report'

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    exported = fields.Boolean(string="Exported", default=False)

    def generate_insurance_report(self):