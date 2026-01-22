# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Repair Custom Extensions',
    'version': '18.0.1.0.0',
    'sequence': 231,
    'category': 'Inventory/Inventory',
    'summary': 'Custom repair extensions with legacy v16 compatibility',
    'description': """
Custom Repair Module Extensions
===============================

This module extends the standard Odoo v18 Repair module with:
- Legacy repair.line model for parts management
- Legacy repair.fee model for service fees
- Invoice method support (before/after repair)
- Warranty expiration date
- Pricelist and currency support
- Quotation notes and internal notes

This module is designed to preserve data migrated from Odoo v16.
""",
    'depends': ['repair', 'sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/repair_custom_views.xml',
        'wizard/repair_make_invoice_views.xml',
        'report/repair_templates_repair_order.xml',
        'data/ir_sequence_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
