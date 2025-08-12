# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
import base64
import requests
import logging
import re
import json

_logger = logging.getLogger(__name__)

class RetainCallHistory(models.Model):
    _name = 'retain.call.history'
    _description = 'Historial de Llamadas'
    _rec_name = 'agent_name'  # Usar agent_name como nombre de display

    # CAMPOS
    sequence = fields.Char(string='Número de Llamada', required=True, readonly=True, default='Nuevo')
    name = fields.Char(string='Nombre del Contacto', required=True, default='Sin nombre')
    phone = fields.Char(string='Teléfono', required=True)
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
    ], string='Estado', default='pending')
    status_var = fields.Selection([
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
    ], string='Estado de proceso', compute='_compute_status_var', store=True)
    call_date = fields.Datetime(string='Fecha y hora de la llamada')
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
    call_id = fields.Char(string='ID de Llamada Retell', readonly=True)
    notes = fields.Text(string='Notas de la llamada')
    transcription = fields.Text(string='Transcripción de la llamada')
    editable = fields.Boolean(string='Editable', default=True)

    # metodo para limpiar y normalizar el texto
    def _clean_text_formatting(self, text):
        if not text:
            return ""
        if isinstance(text, (dict, list)):
            text = json.dumps(text, indent=2, ensure_ascii=False)
        text = str(text)
        _logger.info(f"Texto original (primeros 200): {text[:200]}")
        text = text.replace('\\n', '\n')
        text = text.replace('\\r\\n', '\n')
        text = text.replace('\\r', '\n')
        text = text.replace('\\t', '    ')
        text = text.replace('\\"', '"')
        text = text.replace('\\/', '/')
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = '\n'.join([line.rstrip() for line in text.split('\n')])
        return text.strip()
    #metodo para limpiar y normalizar el texto
    def action_test_transcription_format(self):
        self.ensure_one()  # Solo debe ejecutarse en un registro
        if self.transcription:
            # Mostrar en el log la transcripción original antes de limpiar
            _logger.info(f"Transcripción original: {repr(self.transcription)}")
            # Limpiar y actualizar el campo con el formato correcto
            self.transcription = self._clean_text_formatting(self.transcription)
        # Retornar True para indicar que la acción se ejecutó correctamente
        return True
    # metodo secuencia para generar números de llamada únicos
    # metodo completar campos notes y transcription
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['sequence'] = self.env['ir.sequence'].next_by_code('retain.call.sequence') or 'Nuevo'
            for field in ['transcription', 'notes']:
                if field in vals:
                    vals[field] = self._clean_text_formatting(vals[field])
        return super().create(vals_list)

    # Método para actualizar el registro
    def write(self, vals):
        for field in ['transcription', 'notes']:
            if field in vals:
                vals[field] = self._clean_text_formatting(vals[field])
        return super().write(vals)

    # Método para eliminar el registro y moverlo a la papelera
    def unlink(self):
        for record in self:
            self.env['retain.call.history.trash'].create({
                'sequence': record.sequence,
                'name': record.name,
                'phone': record.phone,
                'call_status': record.call_status,
                'status_var': record.status_var,
                'notes': record.notes,
                'duration': record.duration,
                'duration_ms': record.duration_ms,
                'direction': record.direction,
                'from_number': record.from_number,
                'to_number': record.to_number,
                'agent_name': record.agent_name,
                'disconnection_reason': record.disconnection_reason,
                'call_id': record.call_id,
                'transcription': record.transcription
            })
        return super().unlink()

    # Descargar llamada como archivo de texto
    def action_descargar_llamada(self):
        self.ensure_one()
        contenido = (
            f"Número de Llamada: {self.sequence}\n"
            f"Nombre: {self.name}\n"
            f"Teléfono: {self.phone}\n"
            f"Estado: {self.call_status}\n"
            f"Fecha y Hora: {self.call_date}\n"
            f"Duración: {self.duration} minutos\n"
            f"Notas: {self.notes or ''}\n"
            f"Transcripción: {self.transcription or ''}"
        )
        base64_file = base64.b64encode(contenido.encode('utf-8'))
        return {
            'type': 'ir.actions.act_url',
            'url': (
                f"/web/content/?model=retain.call.history"
                f"&id={self.id}&field=notes&download=true"
                f"&filename=llamada_{self.sequence}.txt"
            ),
            'target': 'self',
        }

    # Método para sincronizar el historial de llamadas (usado por botón y cron)
    def action_sincronizar_historial(self):
        api_key = "key_0f5e8f16b929dac96d750fb43293"
        url = "https://api.retellai.com/v2/list-calls"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        total_llamadas = []
        cursor = None
        while True:
            payload = {"cursor": cursor} if cursor else {}
            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                _logger.error(f"Error en la petición: {e}")
                raise UserError(f"Error al consultar Retell:\n{str(e)}")
            data = response.json()
            llamadas = data.get("calls", []) if isinstance(data, dict) else data
            total_llamadas.extend(llamadas)
            cursor = data.get("next_cursor") if isinstance(data, dict) else None
            if not cursor:
                break

        nuevas, actualizadas = 0, 0
        transcripciones_encontradas = 0
        transcripciones_faltantes = []
        # Primero sincronizar los datos básicos sin transcripciones detalladas
        for llamada in total_llamadas:
            call_id = llamada.get("call_id")
            if not call_id:
                continue
            phone = llamada.get("to_number") or llamada.get("from_number") or ""
            status_raw = llamada.get("call_status", "unknown")
            status = status_raw if status_raw in dict(self._fields['call_status'].selection) else 'unknown'
            start_ts = llamada.get("start_timestamp")
            duration_ms = llamada.get("duration_ms", 0)
            call_date = datetime.utcfromtimestamp(start_ts / 1000.0) if start_ts else False
            duration_min = round(duration_ms / 60000.0, 2)
            analysis = llamada.get("call_analysis", {})
            # Buscar transcripción en los datos del listado primero
            transcription = (
                llamada.get("transcript") or
                llamada.get("transcription") or
                analysis.get("transcript") or
                analysis.get("transcription") or
                analysis.get("call_transcript") or
                ""
            )
            if transcription:
                if isinstance(transcription, list):
                    transcription = '\n'.join(map(str, transcription))
                elif isinstance(transcription, dict):
                    transcription = json.dumps(transcription, indent=2, ensure_ascii=False)
                transcripciones_encontradas += 1

            vals = {
                'call_id': call_id,
                'name': 'Sin nombre',
                'phone': phone,
                'call_status': status,
                'call_date': call_date,
                'duration': duration_min,
                'duration_ms': duration_ms,
                'direction': llamada.get("direction", ""),
                'from_number': llamada.get("from_number", ""),
                'to_number': llamada.get("to_number", ""),
                'agent_name': llamada.get("agent_name", ""),
                'disconnection_reason': llamada.get("disconnection_reason", ""),
                'notes': analysis.get("call_summary", ""),
                'transcription': transcription,
            }
            existing = self.env['retain.call.history'].search([('call_id', '=', call_id)], limit=1)
            if existing:
                existing.write(vals)
                actualizadas += 1
            else:
                self.create(vals)
                nuevas += 1

        # Ahora obtener transcripciones detalladas para llamadas que no las tienen
        llamadas_sin_transcripcion = self.env['retain.call.history'].search([
            '|',
            ('transcription', '=', False),
            ('transcription', '=', '')
        ])

        transcripciones_adicionales = 0

        for llamada in llamadas_sin_transcripcion:
            if not llamada.call_id:
                continue
            try:
                transcript_url = f"https://api.retellai.com/v2/get-call/{llamada.call_id}"
                transcript_response = requests.get(transcript_url, headers=headers)
                if transcript_response.status_code == 200:
                    call_detail = transcript_response.json()
                    # Buscar transcripción en múltiples ubicaciones
                    transcription = (
                        call_detail.get("transcript") or
                        call_detail.get("transcription") or
                        (call_detail.get("call_analysis", {}).get("transcript")) or
                        (call_detail.get("call_analysis", {}).get("transcription")) or
                        ""
                    )
                    if transcription:
                        # Convertir formatos no estándar
                        if isinstance(transcription, list):
                            transcription = '\n'.join(map(str, transcription))
                        elif isinstance(transcription, dict):
                            transcription = json.dumps(transcription, indent=2, ensure_ascii=False)
                        llamada.write({'transcription': transcription})
                        transcripciones_adicionales += 1
                    else:
                        transcripciones_faltantes.append(llamada.call_id)
                else:
                    transcripciones_faltantes.append(llamada.call_id)
            except Exception as e:
                transcripciones_faltantes.append(llamada.call_id)
        # Registrar transcripciones faltantes
        self.action_traducir_motivos_existentes()
        # Estadísticas finales
        llamadas_con_transcripcion = self.env['retain.call.history'].search_count([('transcription', '!=', False), ('transcription', '!=', '')])
        total_llamadas_count = self.env['retain.call.history'].search_count([])
        mensaje = f"Sincronización completada"
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': mensaje,
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def cron_sincronizar_historial(self):
        try:
            self.action_sincronizar_historial()
            _logger.info("Sincronización automática completada")
        except Exception as e:
            _logger.error(f"Error en sincronización automática: {e}")

    def action_traducir_motivos_existentes(self):
        motivo_map = {
            'user_hangup': 'El usuario colgó',
            'agent_hangup': 'El agente colgó',
            'call_transfer': 'Llamada transferida a otro destino',
            'voicemail_reached': 'Se llegó al buzón de voz',
            'inactivity': 'Llamada finalizada por inactividad',
            'max_duration_reached': 'Tiempo máximo de llamada alcanzado',
            'concurrency_limit_reached': 'Límite de llamadas simultáneas alcanzado',
            'no_valid_payment': 'Llamada cancelada por falta de pago válido',
            'scam_detected': 'Llamada finalizada por detección de posible estafa',
            'dial_busy': 'El número estaba ocupado',
            'dial_failed': 'Error al intentar marcar el número',
            'dial_no_answer': 'El número no respondió',
            'invalid_destination': 'Destino inválido',
            'telephony_provider_permission_denied': 'Permiso denegado por el proveedor de telefonía',
            'telephony_provider_unavailable': 'Proveedor de telefonía no disponible',
            'sip_routing_error': 'Error de enrutamiento SIP',
            'marked_as_spam': 'Llamada marcada como spam',
            'user_declined': 'El usuario rechazó la llamada',
            'error_llm_websocket_open': 'Error al abrir la conexión WebSocket del modelo IA',
            'error_llm_websocket_lost_connection': 'Conexión WebSocket con el modelo IA perdida',
            'error_llm_websocket_runtime': 'Error de ejecución en WebSocket del modelo IA',
            'error_llm_websocket_corrupt_payload': 'Paquete de datos corrupto en WebSocket del modelo IA',
            'error_no_audio_received': 'No se recibió audio durante la llamada',
            'error_asr': 'Error en el reconocimiento de voz (ASR)',
            'error_retell': 'Error interno del sistema Retell',
            'error_unknown': 'Error desconocido',
            'error_user_not_joined': 'El usuario no se unió a la llamada',
            'registered_call_timeout': 'Tiempo de espera agotado al registrar la llamada',
            'timeout': 'Tiempo agotado',
            'network_error': 'Error de red',
            'busy': 'Ocupado',
            'no_answer': 'Sin respuesta',
            'rejected': 'Rechazada',
            'completed': 'Completada',
            'unknown': 'Desconocido',
        }
        llamadas = self.env['retain.call.history'].search([])
        for llamada in llamadas:
            motivo_raw = llamada.disconnection_reason
            motivo_es = motivo_map.get(motivo_raw, motivo_raw)
            if motivo_raw != motivo_es:
                llamada.disconnection_reason = motivo_es

    # Computa el estado de la llamada con el status var
    @api.depends('call_status')
    def _compute_status_var(self):
        """Sincroniza status_var con call_status para mostrar textos cortos, solo si es válido"""
        allowed = set(dict(self._fields['status_var'].selection).keys())
        for record in self:
            if record.call_status in allowed:
                record.status_var = record.call_status
            else:
                record.status_var = False