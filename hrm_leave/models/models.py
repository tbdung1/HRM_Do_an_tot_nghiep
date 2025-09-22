# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class hrm_leave(models.Model):
#     _name = 'hrm_leave.hrm_leave'
#     _description = 'hrm_leave.hrm_leave'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

