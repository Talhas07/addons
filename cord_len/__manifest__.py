# -*- coding: utf-8 -*-
{
    "name": "cord_len",

    "summary": """Cord Length""",

    "description": """Cord Length (Pty) Limited Odoo 16 Customisations
    """,

    "author": "Regious (Private) Limited",
    "website": "http://www.regious.co.zw",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Uncategorized",
    "version": "0.1",

    # any module necessary for this one to work correctly
    "depends": ["account","base","repair","web"],

    # always loaded
    "data": [
        # "security/ir.model.access.csv",
        "views/layouts.xml",
        "views/repair.xml",
        "views/invoice.xml",
        "reports/insurance.xml",
    ],
    # only loaded in demonstration mode
    "demo": [
        "demo/demo.xml",
    ],
}
