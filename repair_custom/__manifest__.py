{
    'name': 'Repairs: Custom Fees Restoration',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Restores Repair Fees from v16 for v18',
    'description': """
    Restores the 'Repair Fees' functionality that was present in Odoo v16 but removed in v18.
    This allows access to migrated repair fee data.
    """,
    'depends': ['repair', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/repair_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
