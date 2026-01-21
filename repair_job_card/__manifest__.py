{
    'name': 'Repair Job Card',
    'version': '18.0.1.0.0',
    'category': 'Repair Management',
    'license': 'LGPL-3',
    'summary': 'Manage Job Cards for Repair Orders',
    'author': 'NSMC',
    'depends': ['product', 'base'],
    'data': [
        'views/job_card_views.xml',
       # 'security/job_card_security.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
