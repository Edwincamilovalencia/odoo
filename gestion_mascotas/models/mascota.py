# -*- coding: utf-8 -*-
"""
Modelo de datos para Mascotas
=============================

Este archivo define el modelo principal del módulo.
Un modelo en Odoo representa una tabla en la base de datos.
"""

# Importaciones necesarias de Odoo
from odoo import models, fields

class Mascota(models.Model):
    """
    Modelo para gestionar información de mascotas
    
    Este modelo hereda de models.Model que es la clase base
    para todos los modelos de Odoo.
    """
    
    # === ATRIBUTOS ESPECIALES DEL MODELO ===
    # Nombre técnico del modelo (se convierte en tabla de BD)
    _name = 'gestion.mascota'
    
    # Descripción del modelo para logs y documentación
    _description = 'Modelo para gestionar mascotas'

    # === DEFINICIÓN DE CAMPOS ===
    # Campo de texto obligatorio - será el título del registro
    name = fields.Char(
        string='Nombre de la Mascota',  # Etiqueta en la interfaz
        required=True,                  # Campo obligatorio
        help='Ingrese el nombre de la mascota'
    )
    
    # Campo numérico entero
    edad = fields.Integer(
        string='Edad',
        help='Edad de la mascota en años'
    )
    
    # Campo de texto para el dueño
    propietario = fields.Char(
        string='Nombre del Propietario',
        help='Nombre completo del dueño de la mascota'
    )
    
    # Campo de texto largo para observaciones
    descripcion = fields.Text(
        string='Descripción',
        help='Información adicional sobre la mascota'
    )
