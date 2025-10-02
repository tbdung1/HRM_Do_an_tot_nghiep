from odoo import api, fields, models, _

class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    job_level = fields.Selection(
        [
            ("intern", "Intern"),
            ("staff", "Staff"),
            ("senior", "Senior"),
            ("lead", "Lead"),
            ("manager", "Manager"),
            ("director", "Director"),
            ("executive", "Executive"),
        ],
        string="Job Level",
    )
