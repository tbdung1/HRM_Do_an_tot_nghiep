from odoo import models, fields, api

class HRMJob(models.Model):
    _inherit = 'hr.applicant'  # kế thừa model gốc
