# -*- coding: utf-8 -*-
{
    'name': "Presupuestos Financieros - Odoo Xpert SAS",

    'summary': """
       Presupuestos Financieros""",

    'description': """
        Presupuestos Financieros
    """,

    'author': "Odoo Xpert SAS",
    'website': "https://www.odooxp.com",

    'category': 'Services',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'stock', 'project'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/account_budget.xml',
        'views/account_budget_item.xml',
        'views/menus.xml',
        'views/account_budget_line_form.xml',
    ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
