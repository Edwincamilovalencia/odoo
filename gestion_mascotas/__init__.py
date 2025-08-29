# -*- coding: utf-8 -*-
"""
===========================================
ARCHIVO DE INICIALIZACIÓN PRINCIPAL
===========================================

Este archivo le dice a Python qué carpetas/archivos importar
cuando se carga el módulo.

IMPORTANTE: Este archivo SIEMPRE debe llamarse __init__.py
"""

# Importa toda la carpeta 'models'
# Python buscará el archivo models/__init__.py y ejecutará sus importaciones
from . import models

"""
NOTAS PARA EL PRACTICANTE:
=========================

1. El punto (.) significa "desde la carpeta actual"
2. 'from . import models' = "desde aquí, importa la carpeta models"
3. Si agregas más carpetas (views, controllers), añádelas aquí
4. Este archivo puede estar vacío, pero debe existir
5. Sin este archivo, Python no reconoce la carpeta como módulo

ESTRUCTURA TÍPICA DE IMPORTACIONES:
from . import models      # Modelos de datos
from . import controllers # Controladores web
from . import wizards     # Asistentes/wizards
"""
