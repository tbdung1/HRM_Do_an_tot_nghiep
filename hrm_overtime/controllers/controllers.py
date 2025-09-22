# -*- coding: utf-8 -*-
# from odoo import http


# class HrmOvertime(http.Controller):
#     @http.route('/hrm_overtime/hrm_overtime', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hrm_overtime/hrm_overtime/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hrm_overtime.listing', {
#             'root': '/hrm_overtime/hrm_overtime',
#             'objects': http.request.env['hrm_overtime.hrm_overtime'].search([]),
#         })

#     @http.route('/hrm_overtime/hrm_overtime/objects/<model("hrm_overtime.hrm_overtime"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hrm_overtime.object', {
#             'object': obj
#         })

