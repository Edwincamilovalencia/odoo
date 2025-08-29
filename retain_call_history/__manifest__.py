# -*- coding: utf-8 -*-
{
    'name': "practica odoo",
    'summary': "Módulo de práctica en Odoo 17",
    'description': """
Este módulo fue creado como práctica para aprender desarrollo en Odoo 17.
    """,
    'author': "Edwin Camilo Valencia Bustamante",
    'website': "https://www.tusitio.com",
    'category': 'Tools',
    'version': '0.9',
    'depends': ['base', 'web'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/trash_cron.xml',
        'data/sync_cron.xml',
        'views/llamada_views.xml',
        'views/llamada_trash_views.xml',
        'views/llamada_settings_views.xml',
    'views/templates.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'retain_call_history/static/src/js/retain_call_filters.js',
            'retain_call_history/static/src/scss/retain_call_filters.scss',
            'retain_call_history/static/src/xml/retain_call_filters.xml',
        ],
    },
    'installable': True,
    'application': True,
}
