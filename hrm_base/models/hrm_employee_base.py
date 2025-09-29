from odoo import models, fields, api, _


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"  # ✅ Inherit base của Odoo
    # KHÔNG có _name → KHÔNG tạo model mới
    # KHÔNG tạo table mới

    # ✅ Bổ sung fields vào hr.employee.base có sẵn
    person_phone = fields.Char("Personal Phone")
    person_email = fields.Char("Personal Email")


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
