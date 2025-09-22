# -*- coding: utf-8 -*-
# from odoo import http


# class HrmContract(http.Controller):
#     @http.route('/hrm_contract/hrm_contract', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hrm_contract/hrm_contract/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hrm_contract.listing', {
#             'root': '/hrm_contract/hrm_contract',
#             'objects': http.request.env['hrm_contract.hrm_contract'].search([]),
#         })

#     @http.route('/hrm_contract/hrm_contract/objects/<model("hrm_contract.hrm_contract"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hrm_contract.object', {
#             'object': obj
#         })

