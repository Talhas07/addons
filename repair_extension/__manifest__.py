# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Repair Extension - Custom Fields',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Adds custom fields and diagnostic reports to repair orders',
    'description': """
Repair Extension Module for Odoo 18
====================================

This module extends the standard Repair module with additional features:

Custom Fields:
--------------
* Manual Job Card Number - Internal reference for cross-referencing
* Appliance Serial Number - For warranty tracking and traceability
* Supplier - Link to supplier for procurement and warranty claims
* Fault Description - Detailed fault information
* Diagnosis Notes - Technical diagnosis details
* Repair Recommendations - Technician recommendations

Reports:
--------
* Diagnostic Technical Report - Comprehensive diagnostic report for:
  - Technician assessments
  - Customer communication
  - Warranty claims
  - Internal quality control

This module is designed to work alongside the standard Odoo 18 repair module.
""",
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['repair', 'stock', 'sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/repair_views.xml',
        'report/diagnostic_report.xml',
        'report/diagnostic_report_template.xml',
        'wizard/generate_diagnostic_report_views.xml',
        'data/mail_template_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
