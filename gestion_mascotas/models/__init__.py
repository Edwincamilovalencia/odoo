# -*- coding: utf-8 -*-
"""
===========================================
INICIALIZACIÓN DE MODELOS
===========================================

Este archivo importa todos los modelos de datos del módulo.
Cada archivo .py que contenga un modelo debe ser importado aquí.
"""

# Importa el archivo mascota.py que contiene el modelo Mascota
from . import mascota

"""
=========================

1. Cada archivo de modelo debe importarse aquí
2. Si creas más modelos (ej: veterinario.py), añádelos:
   from . import veterinario
3. El orden de importación generalmente no importa
4. Sin esta importación, Odoo no reconocerá tus modelos

EJEMPLO CON MÚLTIPLES MODELOS:
from . import mascota
from . import propietario  
from . import veterinario
from . import cita
"""
