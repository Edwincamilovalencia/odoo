from ast import Not, Store
from email.policy import default
from itertools import count
from pickle import FALSE
import requests
import json
from tkinter import E
import string
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import datetime, timedelta, date, time
from dateutil.relativedelta import relativedelta
import time
import threading
import pytz

class ProjectFase(models.Model):

    _name = 'project.fase.requisito'
    _description = 'Requisitos de la fase del proyecto'

    project_id = fields.Many2one('project.project', string='Proyecto', required=True)
    fase = fields.Selection([
        ('propuesta', 'Propuesta'),
        ('formulacion', 'Formulación'),
        ('planeacion', 'Planeación'),
        ('ejecucion', 'Ejecución'),
        ('cierre', 'Cierre'),
        ], string='Fase', default='propuesta', required=True)
    name = fields.Char('Requisito', required=True)
    nota = fields.Text('Nota')
    adjunto = fields.Binary(string='Adjunto', attachment=True)
    adjunto_name = fields.Char(string="Adjunto", readonly=False, copy=False)
    visible = fields.Boolean(string='Visible', readonly=True, compute='_compute_proyecto_iniciado')
    completed = fields.Boolean(string='Completado', store=True, readonly=True, compute='_compute_complete')
    project_fase = fields.Boolean(string='Fase proyecto', readonly=True, compute='_compute_fase_proyecto')

    @api.depends('project_id')
    def _compute_proyecto_iniciado(self):
        
        for line in self:
            estado = True
            if line.project_id.pro_fase == 'borrador':
                estado = False
            
            line.update({
                'visible':estado,
            })
    
    @api.depends('project_id')
    def _compute_fase_proyecto(self):
        for requisito in self:
            estado = False
            if requisito.project_id.pro_fase == requisito.fase:
                estado = True

            requisito.update({
                'project_fase': estado,
            })

    @api.depends('nota', 'adjunto')
    def _compute_complete(self):

        linea_completada = False

        for linea in self:
            if linea.nota and linea.adjunto:
                linea_completada = True

            linea.update({
                'completed':linea_completada,
            })

class ProjectProjectExt(models.Model):

    _inherit = 'project.project'

    pro_fase = fields.Selection([
        ('borrador', 'Borrador'),
        ('propuesta', 'Propuesta'),
        ('formulacion', 'Formulación'),
        ('planeacion', 'Planeación'),
        ('ejecucion', 'Ejecución'),
        ('cierre', 'Cierre'),
        ], string='Fase', readonly=True, copy=False, index=True, tracking=3, group_expand='_expand_groups', default='borrador')
    
    @api.model
    def _expand_groups(self, states, domain, order):
        return ['borrador', 'propuesta', 'formulacion', 'planeacion', 'ejecucion', 'cierre']


    pro_lider = fields.Many2one('res.partner', string='Líder')
    pro_componentes_ids = fields.One2many('project.task', 'project_id', string='Componentes', compute="_get_componentes_ids")
    pro_porcentaje_ejecucion = fields.Integer(string='Porcentaje de Ejecución', store=False, compute='_get_porcentaje_ejecucion')
    pro_requisitos_ids = fields.One2many('project.fase.requisito', 'project_id', string='Requisitos del proyecto', readonly=False, compute='_get_requisitos_ids', store=True)
    pro_cierre_forzado = fields.Boolean('Cerrar con pendientes?')
    member_pro_ids = fields.Many2many(comodel_name="res.partner", string="Colaboradores", compute='_get_all_members', store=True)
    
    def _get_all_members(self):

        for proyecto in self:
            usuarios = []
            for componente in proyecto.pro_componentes_ids:
                for actividad in componente.pro_unidades_ids:
                    if actividad.pro_responsable_id:
                        usuarios.append(actividad.pro_responsable_id.id)
                    for tarea in actividad.pro_unidades_ids:
                        if tarea.pro_responsable_id:
                            usuarios.append(tarea.pro_responsable_id.id)

        for record in self:
            record.member_pro_ids = self.env['res.partner'].search([('id', 'in', usuarios)])

    def _get_componentes_ids(self):
        for proyecto in self:
            proyecto.pro_componentes_ids = proyecto.pro_componentes_ids.search([('pro_tipo', '=', 'componente'),('project_id', '=', proyecto.id)])

    def _get_requisitos_ids(self):
        if self.pro_fase == 'borrador':
            self.pro_requisitos_ids = self.pro_requisitos_ids.search([('project_id', '=', self.id)])
        else:
            self.pro_requisitos_ids = self.pro_requisitos_ids.search([('project_id', '=', self.id), ('fase', '=', self.pro_fase)])


    @api.model
    @api.depends('pro_componentes_ids')
    def _get_porcentaje_ejecucion(self):
        for proyecto in self:
            total_ejecutado = 0

            for componente in proyecto.pro_componentes_ids:
                if componente.pro_tipo == 'componente':
                    total_ejecutado += (componente.pro_porcentaje_ejecucion * componente.pro_peso) / 100

            proyecto.pro_porcentaje_ejecucion = total_ejecutado

    def action_adicionar_unidad(self):

        for proyecto in self:
            total_peso = 0

            for componente in proyecto.pro_componentes_ids:
                total_peso += componente.pro_peso

            if total_peso >= 100:
                raise ValidationError("No puede adicionar un componente sin primero ajustar el peso de alguno de ellos para que la suma con el nuevo componente no supere el 100%")

            if not proyecto.date:
                raise ValidationError('No puede adicionar componentes al proyecto sin antes asignar una fecha de finalización aproximada del mismo')

            vals = {
                'project_id': proyecto.id,
                'pro_tipo': 'componente',
                'pro_parent_id': False,
                'name': 'Nuevo componente',
                'pro_peso': 100 - total_peso,
            }

            unidad = self.env['project.task'].create(vals)

    @api.model
    def action_start(self, vals):
        proyecto = self.env['project.project'].search([('id', '=', vals)])
        proyecto.pro_fase = 'propuesta'

    @api.model
    def action_next(self, vals):
        proyecto = self.env['project.project'].search([('id', '=', vals)])

        requisitos_no_cumplidos = self.env['project.fase.requisito'].search_count([('project_id', '=', proyecto.id), ('fase', '=', proyecto.pro_fase), ('completed', '!=', True)])

        if requisitos_no_cumplidos > 0:
            raise ValidationError('No puede finalizar una fase si no ha cumplido con todos los requisitos')

        if proyecto.pro_fase == 'propuesta':
            proyecto.pro_fase = 'formulacion'
        elif proyecto.pro_fase == 'formulacion':
            proyecto.pro_fase = 'planeacion'
        elif proyecto.pro_fase == 'planeacion':
             
            total_peso = 0
            for componente in proyecto.pro_componentes_ids:
                total_peso = total_peso + componente.pro_peso
            
            if total_peso != 100:
                raise ValidationError('El peso total de los componentes debe ser igual al 100% antes de cambiar a fase de ejecución.')
            proyecto.pro_fase = 'ejecucion'
        elif proyecto.pro_fase == 'ejecucion':
            tareas_sin_cerrar = 0
            for componente in proyecto.pro_componentes_ids:
                if componente.pro_unidades_ids:
                    for actividad in componente.pro_unidades_ids:
                        if actividad.pro_unidades_ids:
                            for tarea in actividad.pro_unidades_ids:
                                if not tarea.is_closed:
                                    tareas_sin_cerrar = tareas_sin_cerrar + 1

            if tareas_sin_cerrar > 0 and not proyecto.pro_cierre_forzado:
                raise ValidationError('No puede cerrar un proyecto con tareas pendientes')
            
            proyecto.pro_fase = 'cierre'

            for componente in proyecto.pro_componentes_ids:
                if componente.pro_unidades_ids:
                    for actividad in componente.pro_unidades_ids:
                        if actividad.pro_unidades_ids:
                            for tarea in actividad.pro_unidades_ids:
                                tarea.is_closed = True
    
class ProjectTaskExt(models.Model):

    _inherit = 'project.task'

    pro_tipo = fields.Selection([
        ('componente', 'Componente'),
        ('actividad', 'Actividad'),
        ('tarea', 'Tarea'),
        ], string='Tipo', readonly=True, copy=False, index=True, tracking=3, default='componente')
    pro_parent_id = fields.Many2one('project.task', string='Padre')
    date_end = fields.Datetime('Fecha Finalización')
    pro_porcentaje_ejecucion_tarea = fields.Integer(string='Porcentaje de Ejecución')
    pro_porcentaje_ejecucion = fields.Integer(string='Porcentaje de Ejecución', store=False, compute='_get_porcentaje_ejecucion')
    pro_tipo_tarea = fields.Selection([
        ('cualitativa', 'Cualitativa'),
        ('cuantitativa', 'Cuantitativa'),
        ], string='Tipo', copy=False, index=True, tracking=3, default='cuantitativa')
    pro_ejecutada = fields.Boolean('Ejecutada?', required=False)
    pro_detalle = fields.Text('Detalle de la tarea')
    pro_peso = fields.Float(string='Peso')
    pro_unidades_ids = fields.One2many('project.task', 'pro_parent_id', string='Hijos')
    pro_responsable_id = fields.Many2one('res.partner', string='Responsable', required=False)
    ini_ejec = fields.Boolean(string='Ejecucion', readonly=True, compute='_compute_ejecucion_iniciada')
    date_start = fields.Datetime()
    is_closed = fields.Boolean(string='Cerrada', readonly=True, store=True)

    @api.depends('pro_tipo')
    def _compute_ejecucion_iniciada(self):
        
        for tarea in self:
            estado = True
            if tarea.pro_tipo == 'tarea':
                if tarea.pro_parent_id.pro_parent_id.project_id.pro_fase == 'planeacion':
                    estado = False
            if tarea.pro_tipo == 'actividad':
                if tarea.pro_parent_id.project_id.pro_fase == 'planeacion':
                    estado = False
            if tarea.pro_tipo == 'componente':
                if tarea.project_id.pro_fase == 'planeacion':
                    estado = False
            
            tarea.update({
                'ini_ejec': estado,
            })

    @api.model
    def action_close(self, vals):
        tarea = self.env['project.task'].search([('id', '=', vals)])
        
        if tarea.pro_porcentaje_ejecucion_tarea == 100:
            tarea.is_closed = True
        else:
            raise ValidationError('No puede cerrar una tarea que no se ha ejecutado en su totalidad.')
        
        

    def action_adicionar_unidad(self):
        if self.pro_tipo == 'componente':

            if self.project_id.pro_fase != 'planeacion':
                raise ValidationError('No se encuentra en una fase válida para adición de actividades')

            vals = {
                'project_id': self.project_id.id,
                'pro_tipo': 'actividad',
                'pro_parent_id': self.id,
                'name': 'Nueva actividad'
            }
    
        
        if self.pro_tipo == 'actividad':
            if self.pro_parent_id.project_id.pro_fase != 'planeacion':
                raise ValidationError('No se encuentra en una fase válida para adición de tareas')

            vals = {
                'project_id': self.project_id.id,
                'pro_tipo': 'tarea',
                'pro_parent_id': self.id,
                'name': 'Nueva tarea'
            }

        unidad = self.env['project.task'].create(vals)

    @api.onchange('pro_porcentaje_ejecucion_tarea')
    def _validar_restriccion_ejecucion(self):
        
        if self.pro_porcentaje_ejecucion_tarea > 100:
            raise ValidationError('El porcentaje de ejecución de una tarea no puede superar el 100%')

        if self.pro_porcentaje_ejecucion_tarea < self._origin.pro_porcentaje_ejecucion_tarea and self.pro_tipo_tarea == 'cuantitativa':
            raise ValidationError('No puede asignar un porcentaje de ejecución inferior al actual.')



    @api.onchange('date_end')
    def _validar_fecha_padre(self):
        for tarea in self:
            if tarea.pro_parent_id.date_end and tarea.pro_tipo == 'tarea':
                if tarea.pro_parent_id.date_end < tarea.date_end:
                    raise ValidationError('No puede asignar una fecha de finalización superior a la fecha de la actividad a la cual está asociando la tarea.')
            
            if tarea.project_id.date_start and tarea.pro_tipo == 'actividad':
                if tarea.project_id.date < tarea.date_end.date(): 
                    raise ValidationError('No puede asignar una fecha de finalización superior a la fecha del proyecto.')

    @api.model
    @api.depends('pro_tipo_tarea', 'pro_porcentaje_ejecucion_tarea', 'pro_unidades_ids', 'pro_ejecutada')
    def _get_porcentaje_ejecucion(self):
        for tarea in self:
            if tarea.pro_tipo == 'tarea':                
                if tarea.pro_tipo_tarea == 'cualitativa' and tarea.pro_ejecutada:
                    tarea.pro_porcentaje_ejecucion = 100
                    tarea.pro_porcentaje_ejecucion_tarea = 100
                
                if tarea.pro_tipo_tarea == 'cualitativa' and not tarea.pro_ejecutada:
                    tarea.pro_porcentaje_ejecucion = 0
                    tarea.pro_porcentaje_ejecucion_tarea = 0

                if tarea.pro_tipo_tarea == 'cuantitativa':
                    tarea.pro_porcentaje_ejecucion = tarea.pro_porcentaje_ejecucion_tarea

            if tarea.pro_tipo in ('actividad','componente'):
                num_registros = 0
                total_ejecutado = 0
                for t in tarea.pro_unidades_ids:
                    num_registros +=1
                    total_ejecutado = total_ejecutado + t.pro_porcentaje_ejecucion

                if num_registros == 0:    
                    total_ejecutado = 0
                else:
                    total_ejecutado = total_ejecutado/num_registros
                
                tarea.pro_porcentaje_ejecucion = total_ejecutado

    @api.model
    @api.onchange('pro_tipo_tarea')
    def _onchange_tipo_tarea(self):
        if self.pro_tipo_tarea == 'cualitativa':
            self.pro_porcentaje_ejecucion_tarea = 0
        else:
            self.pro_ejecutada = False

    def action_open(self):
        return {
            'name': self.name,
            'view_mode': 'form',
            'view_id': False,
            'res_model': self._name,
            'domain': [],
            'context': dict(self._context, active_ids = self.ids),
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': self.id
        }
        