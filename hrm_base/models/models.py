# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class hrm_base(models.Model):
#     _name = 'hrm_base.hrm_base'
#     _description = 'hrm_base.hrm_base'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

