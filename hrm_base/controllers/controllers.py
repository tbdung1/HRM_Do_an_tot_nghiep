# -*- coding: utf-8 -*-
# from odoo import http


# class HrmBase(http.Controller):
#     @http.route('/hrm_base/hrm_base', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hrm_base/hrm_base/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hrm_base.listing', {
#             'root': '/hrm_base/hrm_base',
#             'objects': http.request.env['hrm_base.hrm_base'].search([]),
#         })

#     @http.route('/hrm_base/hrm_base/objects/<model("hrm_base.hrm_base"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hrm_base.object', {
#             'object': obj
#         })

