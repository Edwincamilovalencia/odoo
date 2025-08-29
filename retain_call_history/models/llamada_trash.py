# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta

class RetainCallHistoryTrash(models.Model):
    _name = 'retain.call.history.trash'
    _description = 'Historial de Llamadas Eliminadas'

    sequence = fields.Char(string='Número de Llamada', readonly=True)
    name = fields.Char(string='Nombre del Contacto', required=True)
    phone = fields.Char(string='Teléfono', required=True)
    # Alinear con los estados del modelo principal retain.call.history
    call_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('registered', 'Iniciando'),
        ('ongoing', 'Activa'),
        ('ended', 'Finalizada'),
        ('not_connected', 'Sin conexión'),
        ('invalid_destination', 'Destino inválido'),
        ('telephony_provider_permission_denied', 'Permiso denegado'),
        ('telephony_provider_unavailable', 'Proveedor no disp.'),
        ('sip_routing_error', 'Error de ruta'),
        ('marked_as_spam', 'Spam'),
        ('user_declined', 'Rechazada'),
        ('unknown', 'Desconocida'),
    ], string='Estado')
    deletion_date = fields.Datetime(
        string='Fecha de eliminación',
        default=fields.Datetime.now,
        readonly=True
    )
    description_llamada = fields.Text(string='Descripción de la llamada')
    duration = fields.Float(string='Duración (minutos)')
    duration_ms = fields.Integer(string='Duración (ms)')
    direction = fields.Selection([
        ('inbound', 'Entrante'),
        ('outbound', 'Saliente')
    ], string='Dirección de la llamada')
    from_number = fields.Char(string='Número origen')
    to_number = fields.Char(string='Número destino')
    agent_name = fields.Char(string='Nombre del agente')
    disconnection_reason = fields.Char(string='Motivo de desconexión')
    call_id = fields.Char(string='ID de Llamada Retell')
    transcription = fields.Text(string='Transcripción de la llamada')

    # Método para restaurar el registro eliminado
    def action_restore(self):
        self.env['retain.call.history'].create({
            'sequence': self.sequence,
            'name': self.name,
            'phone': self.phone,
            'call_status': self.call_status,
            'description_llamada': self.description_llamada,
            'duration': self.duration,
            'duration_ms': self.duration_ms,
            'direction': self.direction,
            'from_number': self.from_number,
            'to_number': self.to_number,
            'agent_name': self.agent_name,
            'disconnection_reason': self.disconnection_reason,
            'call_id': self.call_id,
            'transcription': self.transcription,
        })
        self.unlink()

    # Elimina los registros de la papelera que tengan más de 7 días
    @api.model
    def _cron_delete_old_records(self):
        deadline = fields.Datetime.now() - timedelta(days=7)
        self.search([('deletion_date', '<', deadline)]).unlink()
