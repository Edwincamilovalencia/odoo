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
    _rec_name = 'agent_name'

    sequence = fields.Char(string='Número de Llamada', required=True, readonly=True, default='Nuevo')
    name = fields.Char(string='Nombre del Contacto', required=True, default='Sin nombre')
    phone = fields.Char(string='Teléfono', required=True)
    call_status = fields.Selection([('pending', 'Pendiente'),('registered', 'Iniciando'),('ongoing', 'Activa'),('ended', 'Finalizada'),('not_connected', 'Sin conexión'),
        ('invalid_destination', 'Destino inválido'),('telephony_provider_permission_denied', 'Permiso denegado'),('telephony_provider_unavailable', 'Proveedor no disp.'),
        ('sip_routing_error', 'Error de ruta'),('marked_as_spam', 'Spam'),('user_declined', 'Rechazada'),
    ], string='Estado', default='pending')
    status_var = fields.Selection([
        ('registered', 'Iniciando'),('ongoing', 'Activa'),('ended', 'Finalizada'),('not_connected', 'Sin conexión'),('invalid_destination', 'Destino inválido'),
        ('telephony_provider_permission_denied', 'Permiso denegado'),('telephony_provider_unavailable', 'Proveedor no disp.'),
        ('sip_routing_error', 'Error de ruta'),('marked_as_spam', 'Spam'),('user_declined', 'Rechazada'),
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
    description_llamada = fields.Text(string='Descripción de la llamada')
    transcription = fields.Text(string='Transcripción de la llamada')
    editable = fields.Boolean(string='Editable', default=True)

    def _clean_text_formatting(self, text):
        """Limpia y normaliza el formato del texto para transcripciones y descripción"""
        if not text:
            return ""
        # Convierte listas o diccionarios a string en formato JSON
        if isinstance(text, (dict, list)):
            text = json.dumps(text, indent=2, ensure_ascii=False)
        # Asegura que el texto sea string
        text = str(text)
        # Sólo log en modo debug para evitar spam en logs
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug(f"Limpiando texto (primeros 200 chars): {text[:200]}")
        text = text.replace('\\n', '\n')
        text = text.replace('\\r\\n', '\n')
        text = text.replace('\\r', '\n')
        text = text.replace('\\t', '    ')
        text = text.replace('\\"', '"')
        text = text.replace('\\/', '/')
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = '\n'.join([line.rstrip() for line in text.split('\n')])
        return text.strip()

    def _get_retell_headers(self):
        api_key = "key_0f5e8f16b929dac96d750fb43293"
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    # Busca el nombre del agente en los datos
    def _search_agent_name_in_data(self, data_dict, analysis_dict=None):
        agent_fields = [
            'agent_name', 'agent', 'assistant_name', 'assistant',
            'agent_id', 'assistant_id', 'bot_name', 'bot_id',
            'voice_agent', 'ai_agent', 'virtual_agent'
        ]

        # Buscar en el nivel principal
        for field in agent_fields:
            if data_dict.get(field):
                return data_dict.get(field)

        # Buscar en call_analysis si existe
        if analysis_dict:
            for field in agent_fields:
                if analysis_dict.get(field):
                    return analysis_dict.get(field)

        # Buscar en objetos anidados
        for key, value in data_dict.items():
            if isinstance(value, dict):
                for field in agent_fields:
                    if value.get(field):
                        return value.get(field)
        return ""

    # Busca la transcripción en el diccionario de datos
    def _search_transcription_in_data(self, data_dict, analysis_dict=None):
        transcription = (
            data_dict.get("transcript") or
            data_dict.get("transcription") or
            ""
        )
        if analysis_dict and not transcription:
            transcription = (
                analysis_dict.get("transcript") or
                analysis_dict.get("transcription") or
                analysis_dict.get("call_transcript") or
                ""
            )
        return transcription

    # Test: normaliza la transcripción del registro activo
    def action_test_transcription_format(self):
        self.ensure_one()
        if self.transcription:
            _logger.info(f"Transcripción original: {repr(self.transcription)}")
            self.transcription = self._clean_text_formatting(self.transcription)
        return True

    # Crea nuevos registros asignando secuencia y limpiando texto
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['sequence'] = self.env['ir.sequence'].next_by_code('retain.call.sequence') or 'Nuevo'
            for field in ['transcription', 'description_llamada']:
                if field in vals:
                    vals[field] = self._clean_text_formatting(vals[field])
        return super().create(vals_list)

    # Actualiza registros limpiando el formato del texto
    def write(self, vals):
        for field in ['transcription', 'description_llamada']:
            if field in vals:
                vals[field] = self._clean_text_formatting(vals[field])
        return super().write(vals)

    # Elimina registros moviéndolos a la papelera (tabla retain.call.history.trash)
    def unlink(self):
        for record in self:
            self.env['retain.call.history.trash'].create({
                'sequence': record.sequence,
                'name': record.name,
                'phone': record.phone,
                'call_status': record.call_status,
                'status_var': record.status_var,
                'description_llamada': record.description_llamada,
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

    # Descarga una llamada como archivo de texto (contenido en español)
    def action_descargar_llamada(self):
        self.ensure_one()
        contenido = (
            f"Número de Llamada: {self.sequence}\n"
            f"Nombre: {self.name}\n"
            f"Teléfono: {self.phone}\n"
            f"Estado: {self.call_status}\n"
            f"Fecha y Hora: {self.call_date}\n"
            f"Duración: {self.duration} minutos\n"
            f"Descripción de la llamada: {self.description_llamada or ''}\n"
            f"Transcripción: {self.transcription or ''}"
        )
        base64_file = base64.b64encode(contenido.encode('utf-8'))
        return {
            'type': 'ir.actions.act_url',
            'url': (
                f"/web/content/?model=retain.call.history"
                f"&id={self.id}&field=description_llamada&download=true"
                f"&filename=llamada_{self.sequence}.txt"
            ),
            'target': 'self',
        }

    # Obtiene todas las llamadas de la API de Retell y las trae a Odoo
    def _fetch_all_calls_from_retell(self):
        url = "https://api.retellai.com/v2/list-calls"
        headers = self._get_retell_headers()
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
        return total_llamadas

    # Procesa los datos de una llamada individual de Retell
    def _process_call_data(self, llamada_data):
        call_id = llamada_data.get("call_id")
        if not call_id:
            return None
        phone = llamada_data.get("to_number") or llamada_data.get("from_number") or ""
        status_raw = llamada_data.get("call_status", "unknown")
        status = status_raw if status_raw in dict(self._fields['call_status'].selection) else 'unknown'
        start_ts = llamada_data.get("start_timestamp")
        duration_ms = llamada_data.get("duration_ms", 0)
        call_date = datetime.utcfromtimestamp(start_ts / 1000.0) if start_ts else False
        duration_min = round(duration_ms / 60000.0, 2)
        analysis = llamada_data.get("call_analysis", {})
        # Buscar transcripción
        transcription = self._search_transcription_in_data(llamada_data, analysis)
        if transcription:
            if isinstance(transcription, list):
                transcription = '\n'.join(map(str, transcription))
            elif isinstance(transcription, dict):
                transcription = json.dumps(transcription, indent=2, ensure_ascii=False)
        # Buscar nombre del agente
        agent_name = self._search_agent_name_in_data(llamada_data, analysis)

        return {
            'call_id': call_id,
            'name': 'Sin nombre',
            'phone': phone,
            'call_status': status,
            'call_date': call_date,
            'duration': duration_min,
            'duration_ms': duration_ms,
            'direction': llamada_data.get("direction", ""),
            'from_number': llamada_data.get("from_number", ""),
            'to_number': llamada_data.get("to_number", ""),
            'agent_name': agent_name,
            'disconnection_reason': llamada_data.get("disconnection_reason", ""),
            'description_llamada': analysis.get("call_summary", ""),
            'transcription': transcription,
        }

    # Sincroniza los datos básicos de las llamadas
    def _sync_basic_call_data(self, total_llamadas):
        nuevas, actualizadas = 0, 0
        transcripciones_encontradas = 0

        for i, llamada_data in enumerate(total_llamadas):
            # Log para debug - solo para las primeras 5 llamadas
            if i < 5:
                _logger.info(f"Call ID: {llamada_data.get('call_id')}")
                _logger.info(f"Available keys: {list(llamada_data.keys())}")
                analysis = llamada_data.get("call_analysis", {})
                if analysis:
                    _logger.info(f"Call analysis keys: {list(analysis.keys())}")
            vals = self._process_call_data(llamada_data)
            if not vals:
                continue
            if vals.get('transcription'):
                transcripciones_encontradas += 1
            existing = self.env['retain.call.history'].search([('call_id', '=', vals['call_id'])], limit=1)
            if existing:
                existing.write(vals)
                actualizadas += 1
            else:
                self.create(vals)
                nuevas += 1
        return nuevas, actualizadas, transcripciones_encontradas

    def action_sincronizar_historial(self):
        try:
            _logger.info("Iniciando sincronización de llamadas desde Retell...")
            total_llamadas = self._fetch_all_calls_from_retell()
            _logger.info(f"Obtenidas {len(total_llamadas)} llamadas de Retell")
            nuevas, actualizadas, transcripciones_encontradas = self._sync_basic_call_data(total_llamadas)
            _logger.info(f"Sincronización básica: {nuevas} nuevas, {actualizadas} actualizadas, {transcripciones_encontradas} con transcripción")
            transcripciones_adicionales, agentes_adicionales = self._complete_missing_data()
            agentes_adicionales += self._exhaustive_agent_search()
            self.action_traducir_motivos_existentes()
            return self._show_sync_results(nuevas, actualizadas, transcripciones_adicionales, agentes_adicionales)
        except Exception as e:
            _logger.error(f"Error en sincronización: {e}")
            raise UserError(f"Error durante la sincronización: {str(e)}")

    def _complete_missing_data(self):
        headers = self._get_retell_headers()
        llamadas_incompletas = self.env['retain.call.history'].search([
            '|', '|',
            ('transcription', '=', False),
            ('transcription', '=', ''),
            ('agent_name', '=', '')
        ])
        transcripciones_adicionales = 0
        agentes_adicionales = 0

        for llamada in llamadas_incompletas:
            if not llamada.call_id:
                continue
            try:
                transcript_url = f"https://api.retellai.com/v2/get-call/{llamada.call_id}"
                transcript_response = requests.get(transcript_url, headers=headers)
                if transcript_response.status_code == 200:
                    call_detail = transcript_response.json()
                    analysis_detail = call_detail.get("call_analysis", {})
                    # Buscar transcripción
                    transcription = self._search_transcription_in_data(call_detail, analysis_detail)
                    # Buscar nombre del agente
                    agent_name = self._search_agent_name_in_data(call_detail, analysis_detail)
                    # Preparar datos para actualizar
                    update_vals = {}
                    if transcription and (not llamada.transcription or llamada.transcription == ''):
                        if isinstance(transcription, list):
                            transcription = '\n'.join(map(str, transcription))
                        elif isinstance(transcription, dict):
                            transcription = json.dumps(transcription, indent=2, ensure_ascii=False)
                        update_vals['transcription'] = transcription
                        transcripciones_adicionales += 1
                    if agent_name and (not llamada.agent_name or llamada.agent_name == ''):
                        update_vals['agent_name'] = agent_name
                        agentes_adicionales += 1
                    # Actualizar si hay cambios
                    if update_vals:
                        llamada.write(update_vals)
            except Exception as e:
                _logger.error(f"Error obteniendo detalles para {llamada.call_id}: {e}")
        return transcripciones_adicionales, agentes_adicionales

    # Búsqueda exhaustiva de nombres de agentes para llamadas que aún no tienen nombre de agente
    def _exhaustive_agent_search(self):
        headers = self._get_retell_headers()
        llamadas_sin_agente = self.env['retain.call.history'].search([
            '|',
            ('agent_name', '=', False),
            ('agent_name', '=', '')
        ])
        _logger.info(f"Búsqueda exhaustiva: {len(llamadas_sin_agente)} llamadas sin agente")
        agentes_adicionales = 0
        for llamada in llamadas_sin_agente:
            if not llamada.call_id:
                continue
            try:
                detail_url = f"https://api.retellai.com/v2/get-call/{llamada.call_id}"
                detail_response = requests.get(detail_url, headers=headers)
                if detail_response.status_code == 200:
                    call_detail = detail_response.json()
                    analysis_detail = call_detail.get("call_analysis", {})
                    agent_name = self._search_agent_name_in_data(call_detail, analysis_detail)
                    if agent_name:
                        llamada.write({'agent_name': agent_name})
                        agentes_adicionales += 1
                        _logger.info(f"Agente encontrado para {llamada.call_id}: {agent_name}")
                    else:
                        _logger.info(f"No se encontró agente para {llamada.call_id}. Campos: {list(call_detail.keys())}")
            except Exception as e:
                _logger.error(f"Error obteniendo detalles para {llamada.call_id}: {e}")
        return agentes_adicionales

    # Muestra los resultados de la sincronización
    def _show_sync_results(self, nuevas, actualizadas, transcripciones_adicionales, agentes_adicionales):
        llamadas_con_transcripcion = self.env['retain.call.history'].search_count([
            ('transcription', '!=', False), ('transcription', '!=', '')
        ])
        llamadas_con_agente = self.env['retain.call.history'].search_count([
            ('agent_name', '!=', False), ('agent_name', '!=', '')
        ])
        total_llamadas_count = self.env['retain.call.history'].search_count([])
        mensaje = f"Sincronización completada."
        _logger.info(f"Resultados finales - Total: {total_llamadas_count}, Nuevas: {nuevas}, "
                    f"Actualizadas: {actualizadas}, Con agente: {llamadas_con_agente}, "
                    f"Agentes adicionales: {agentes_adicionales}")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': mensaje,
                'type': 'success',
                'sticky': False,
            }
        }

    # Método para ejecutar sincronización automática vía cron
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

    # Computa el campo status_var basado en call_status
    @api.depends('call_status')
    def _compute_status_var(self):
        allowed = set(dict(self._fields['status_var'].selection).keys())
        for record in self:
            if record.call_status in allowed:
                record.status_var = record.call_status
            else:
                record.status_var = False