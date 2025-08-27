# -*- coding: utf-8 -*-
{
    'name': 'Monitoreo Agente',
    'version': '1.0',
    'summary': 'Modulo para monitoreo de agentes',
    'description': 'Modulo Odoo para monitorear agentes.',
    'license': 'LGPL-3',
    'author': 'Tu Nombre',
    'category': 'Tools',
    'depends': ['base'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/dashboard_data.xml',
        'views/monitoreo_agent_views.xml',
        'views/monitoreo_call_views.xml',
        'views/monitoreo_alert_views.xml',
        'views/monitoreo_dashboard_views.xml',
        'views/monitoreo_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
