# -*- coding: utf-8 -*-
# from odoo import http


# class HrmAttendanceIntegration(http.Controller):
#     @http.route('/hrm_attendance_integration/hrm_attendance_integration', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hrm_attendance_integration/hrm_attendance_integration/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hrm_attendance_integration.listing', {
#             'root': '/hrm_attendance_integration/hrm_attendance_integration',
#             'objects': http.request.env['hrm_attendance_integration.hrm_attendance_integration'].search([]),
#         })

#     @http.route('/hrm_attendance_integration/hrm_attendance_integration/objects/<model("hrm_attendance_integration.hrm_attendance_integration"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hrm_attendance_integration.object', {
#             'object': obj
#         })

