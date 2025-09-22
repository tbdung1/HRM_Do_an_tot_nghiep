# -*- coding: utf-8 -*-
# from odoo import http


# class HrmRecruitment(http.Controller):
#     @http.route('/hrm_recruitment/hrm_recruitment', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hrm_recruitment/hrm_recruitment/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hrm_recruitment.listing', {
#             'root': '/hrm_recruitment/hrm_recruitment',
#             'objects': http.request.env['hrm_recruitment.hrm_recruitment'].search([]),
#         })

#     @http.route('/hrm_recruitment/hrm_recruitment/objects/<model("hrm_recruitment.hrm_recruitment"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hrm_recruitment.object', {
#             'object': obj
#         })

