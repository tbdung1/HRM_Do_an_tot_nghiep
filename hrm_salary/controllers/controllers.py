# -*- coding: utf-8 -*-
# from odoo import http


# class HrmSalary(http.Controller):
#     @http.route('/hrm_salary/hrm_salary', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hrm_salary/hrm_salary/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hrm_salary.listing', {
#             'root': '/hrm_salary/hrm_salary',
#             'objects': http.request.env['hrm_salary.hrm_salary'].search([]),
#         })

#     @http.route('/hrm_salary/hrm_salary/objects/<model("hrm_salary.hrm_salary"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hrm_salary.object', {
#             'object': obj
#         })

