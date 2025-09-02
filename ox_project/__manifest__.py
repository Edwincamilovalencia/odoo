# -*- coding: utf-8 -*-
{
    'name': "Modulo Personalización Proyectos - Odoo Xpert SAS",

    'summary': """
        Modulo Personalización Proyectos""",

    'description': """
        Modulo Personalización Proyectos
    """,

    'author': "Odoo Xpert SAS",
    'website': "https://www.odooxp.com",

    'category': 'Services/Project',
    'version': '1.0',

    'depends': ['base', 'project', 'ox_finantial_budget'], 

    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/menus.xml',
    'views/views.xml',
        'views/project_project.xml',
        'views/stock_picking.xml',
        'views/project_activity_type.xml',
        'views/project_task_views.xml',
        'views/project_specification_wizard_view.xml',
    ],
    
    'demo': [
        'demo/demo.xml',
    ],
    
    'installable': True,
    'application': True,
}
