# -*- coding: utf-8 -*-
"""
===========================================
MANIFIESTO DEL MÓDULO GESTIÓN DE MASCOTAS
===========================================

Este archivo es el corazón del módulo. Define toda la información
necesaria para que Odoo reconozca, instale y configure el módulo.

IMPORTANTE: Este archivo SIEMPRE debe llamarse __manifest__.py
"""

{
    # ===========================================
    # INFORMACIÓN BÁSICA DEL MÓDULO
    # ===========================================
    
    # Nombre que aparece en la lista de aplicaciones
    'name': 'Gestión de Mascotas',
    
    # Versión del módulo (formato recomendado: major.minor.patch)
    'version': '1.0',
    
    # Descripción corta que aparece debajo del nombre
    'summary': 'Ejemplo simple para aprender Odoo',
    
    # Descripción detallada del módulo
    'description': 'Módulo de ejemplo para registrar mascotas y sus dueños.',
    
    # Información del desarrollador
    'author': 'Tu Nombre',
    
    # Sitio web del módulo o desarrollador
    'website': 'https://www.ejemplo.com',
    
    # Categoría donde aparecerá el módulo en la tienda de apps
    'category': 'Tutorial',

    # ===========================================
    # DEPENDENCIAS
    # ===========================================
    
    # Lista de módulos que DEBEN estar instalados antes que este
    'depends': ['base'],  # 'base' es obligatorio en todos los módulos
    
    # ===========================================
    # ARCHIVOS DE DATOS
    # ===========================================
    
    # Lista de archivos que se cargan al instalar el módulo
    # ORDEN IMPORTANTE: Seguridad → Vistas → Menús → Datos
    'data': [
        'security/ir.model.access.csv',  # 1. Permisos de acceso
        'views/mascota_views.xml',       # 2. Vistas de interfaz
        'views/mascota_menu.xml',        # 3. Menús de navegación
    ],
    
    # ===========================================
    # CONFIGURACIÓN DE INSTALACIÓN
    # ===========================================
    
    # Permite que el módulo se pueda instalar
    'installable': True,
    
    # Marca el módulo como aplicación principal
    # (aparece en el panel de aplicaciones, no solo en configuración)
    'application': True,
    
    # Instala automáticamente al instalar Odoo (generalmente False)
    'auto_install': False,
}

"""
NOTAS PARA EL PRACTICANTE:
=========================

1. NUNCA cambies el nombre de este archivo (__manifest__.py)
2. El orden en 'data' es crucial: seguridad primero, menús al final
3. 'depends' debe incluir TODOS los módulos que uses
4. 'application': True hace que aparezca como app principal
5. Si hay errores en este archivo, el módulo no se instalará
"""
