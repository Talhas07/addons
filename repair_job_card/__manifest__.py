{
    'name': 'Repair Job Card',
    'version': '18.0.1.0.0',
    'category': 'Repair Management',
    'license': 'LGPL-3',
    'summary': 'Manage Job Cards for Repair Orders',
    'author': 'NSMC',
    'depends': ['repair', 'repair_extension', 'mail'],
    'data': [
        'security/job_card_security.xml',
        'security/ir.model.access.csv',
        'security/job_card_access_rules.xml',
        'views/job_card_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
