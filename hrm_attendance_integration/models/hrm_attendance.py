from odoo import models, fields, api, exceptions

class HrmAttendance(models.Model):
    _inherit = 'hr.attendance'