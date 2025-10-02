# models/hr_employee.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrmEmployees(models.Model):
    _inherit = "hr.employee"

    update_request_ids = fields.One2many(
        "hrm.employee.update.request", "employee_id", string="Update Requests"
    )
    update_request_count = fields.Integer(
        "Update Request Count", compute="_compute_update_request_count"
    )

    def _compute_update_request_count(self):
        for employee in self:
            employee.update_request_count = len(employee.update_request_ids)

    def action_view_update_requests(self):
        self.ensure_one()
        return {
            "name": _("Update Requests"),
            "type": "ir.actions.act_window",
            "res_model": "hrm.employee.update.request",
            "view_mode": "tree,form",
            "domain": [("employee_id", "=", self.id)],
            "context": {"default_employee_id": self.id},
        }

