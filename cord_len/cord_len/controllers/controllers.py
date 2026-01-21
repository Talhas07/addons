# -*- coding: utf-8 -*-
# from odoo import http


# class CordLen(http.Controller):
#     @http.route('/cord_len/cord_len', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cord_len/cord_len/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('cord_len.listing', {
#             'root': '/cord_len/cord_len',
#             'objects': http.request.env['cord_len.cord_len'].search([]),
#         })

#     @http.route('/cord_len/cord_len/objects/<model("cord_len.cord_len"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cord_len.object', {
#             'object': obj
#         })
