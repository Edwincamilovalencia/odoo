# -*- coding: utf-8 -*-
{
    'name': 'Partidos Políticos',
    'summary': 'Relaciona personas (usuarios) con partidos políticos',
    'description': 'Módulo para gestionar asignación de usuarios a un partido político predefinido.',
    'author': 'Custom',
    'website': '',
    'category': 'Tools',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
    'security/rules.xml',
        'views/partidos_politicos_views.xml',
        'data/partidos_politicos_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'partidos_politicos/static/src/js/welcome_notification.js',
            'partidos_politicos/static/src/js/carga_partido_filter.js',
            'partidos_politicos/static/src/xml/welcome_notification.xml',
            'partidos_politicos/static/src/scss/welcome_notification.scss',
            'partidos_politicos/static/src/scss/carga_partido_filter.scss',
        ],
    },
    'installable': True,
    'application': False,
}
