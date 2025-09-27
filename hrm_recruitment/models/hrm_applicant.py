from odoo import models, fields, api

class HRMApplicant(models.Model):
    _inherit = 'hr.applicant'  # kế thừa model gốc

    email = fields.Char(string="Email")
    phone = fields.Char(string="Số điện thoại")
    degree = fields.Selection([
        ('bachelor', 'Cử nhân'),
        ('master', 'Thạc sĩ'),
        ('phd', 'Tiến sĩ'),
    ], string="Trình độ")
