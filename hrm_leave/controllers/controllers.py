# -*- coding: utf-8 -*-
# from odoo import http


# class HrmLeave(http.Controller):
#     @http.route('/hrm_leave/hrm_leave', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hrm_leave/hrm_leave/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hrm_leave.listing', {
#             'root': '/hrm_leave/hrm_leave',
#             'objects': http.request.env['hrm_leave.hrm_leave'].search([]),
#         })

#     @http.route('/hrm_leave/hrm_leave/objects/<model("hrm_leave.hrm_leave"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hrm_leave.object', {
#             'object': obj
#         })

