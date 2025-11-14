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

class HrmEmployeesPublic(models.Model):
    _inherit = "hr.employee.public"

    # @api.depends()
    # def _compute_update_request_count(self):
    #     for record in self:
    #         employee = self.env["hr.employee"].sudo().browse(record.id)
    #         if employee.exists():
    #             record.update_request_count = len(employee.update_request_ids)
    #         else:
    #             record.update_request_count = 0

    update_request_count = fields.Integer(
        "Update Request Count", related='employee_id.update_request_count', store=False
    )

    def action_view_update_requests(self):
        # Delegate to hr.employee
        employee = self.env["hr.employee"].browse(self.id)
        return employee.action_view_update_requests()
