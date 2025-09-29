from odoo import api, fields, models, _

class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    person_phone = fields.Char(string="Public Phone", readonly=True)
    person_email = fields.Char(string="Public Email", readonly=True)

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
