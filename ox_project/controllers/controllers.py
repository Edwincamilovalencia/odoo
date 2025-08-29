# -*- coding: utf-8 -*-
# from odoo import http


# class PerProyectos(http.Controller):
#     @http.route('/per_proyectos/per_proyectos', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/per_proyectos/per_proyectos/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('per_proyectos.listing', {
#             'root': '/per_proyectos/per_proyectos',
#             'objects': http.request.env['per_proyectos.per_proyectos'].search([]),
#         })

#     @http.route('/per_proyectos/per_proyectos/objects/<model("per_proyectos.per_proyectos"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('per_proyectos.object', {
#             'object': obj
#         })
