from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PartidoPolitico(models.Model):
    _name = 'politico.partido'
    _description = 'Partido Político'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True, index=True)


class PartidoAsignacion(models.Model):
    _name = 'politico.asignacion'
    _description = 'Asignación de usuario a partido político'
    _order = 'user_id'

    user_id = fields.Many2one('res.users', string='Persona', required=True, index=True)
    partido_id = fields.Many2one(
        'politico.partido',
        string='Partido político',
        index=True,
        default=lambda self: self._default_partido_id(),
    )

    _sql_constraints = [
        ('uniq_user', 'unique(user_id)', 'Cada persona solo puede tener un partido político asignado.'),
    ]

    @api.model
    def _default_partido_id(self):
        asign = self.search([('user_id', '=', self.env.user.id)], limit=1)
        return asign.partido_id.id if asign else False

    @api.model
    def get_current_user_assignment(self):
        user = self.env.user
        asign = self.search([('user_id', '=', user.id)], limit=1)
        return {
            'user_id': user.id,
            'user_name': user.name,
            'partido_name': asign.partido_id.name if asign and asign.partido_id else '',
            'is_readonly_user': user.has_group('partidos_politicos.group_partidos_politicos_readonly'),
            # Administrador real del sistema
            'is_admin_user': user.has_group('base.group_system'),
        }

    def name_get(self):
        res = []
        for rec in self:
            name = rec.user_id.name
            if rec.partido_id:
                name = f"{name} - {rec.partido_id.name}"
            res.append((rec.id, name))
        return res


class PartidoCarga(models.Model):
    _name = 'politico.carga'
    _description = 'Registro de cargas de archivos de partido'
    _order = 'upload_datetime desc'

    user_id = fields.Many2one('res.users', string='Persona', default=lambda self: self.env.user, required=True, index=True)
    partido_id = fields.Many2one(
        'politico.partido',
        string='Partido político',
        index=True,
        default=lambda self: self._default_partido_id(),
        readonly=True,
    )
    # Guardar binario como adjunto para poder recuperarlo fácilmente y no devolver solo el tamaño
    upload_file = fields.Binary(string='Archivo', required=True, attachment=True)
    filename = fields.Char(string='Nombre de archivo')
    file_type = fields.Selection(
        [('xlsx', 'Excel (.xlsx)'), ('xls', 'Excel 97-2003 (.xls)'), ('csv', 'CSV')],
        string='Tipo de archivo',
        index=True,
    )
    upload_datetime = fields.Datetime(string='Fecha y hora de carga', default=fields.Datetime.now, required=True)

    @api.model
    def _default_partido_id(self):
        asign = self.env['politico.asignacion'].search([('user_id', '=', self.env.user.id)], limit=1)
        return asign.partido_id.id if asign else False

    @api.onchange('filename')
    def _onchange_filename(self):
        if self.filename:
            ext = self.filename.rsplit('.', 1)[-1].lower()
            self.file_type = ext if ext in ['csv', 'xlsx', 'xls'] else False
        else:
            self.file_type = False

    @api.model
    def create(self, vals):
        allowed_exts = {'csv', 'xlsx', 'xls'}
        filename = vals.get('filename') or ''
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in allowed_exts:
            raise ValidationError(_('Solo se permiten archivos CSV o Excel (.csv, .xlsx, .xls)'))

        vals['file_type'] = ext

        if not vals.get('user_id'):
            vals['user_id'] = self.env.user.id
        if not vals.get('partido_id'):
            asign = self.env['politico.asignacion'].search([('user_id', '=', vals['user_id'])], limit=1)
            if asign:
                vals['partido_id'] = asign.partido_id.id

        return super().create(vals)
