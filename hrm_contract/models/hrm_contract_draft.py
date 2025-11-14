# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmContractDraft(models.Model):
    _name = "hrm.contract.draft"
    _description = "HrmContractDraft"
    _inherit = ["hr.contract", "hr.notification.mixin", "mail.thread"]

    employee_submit = fields.Many2one("hr.employee", "Employee Submit", default=lambda self: self.env.user.employee_id)
    emp_name = fields.Char("Employee Name")
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female"), ("other", "Other")],
        string="Gender",
        required=True,
    )
    permanent_address = fields.Char("Permanent Address")
    residential_address = fields.Char("Residential Address")
    birth_date = fields.Date("Birth Date")

    state_hr_contract = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        group_expand="_expand_states",
        copy=False,
        tracking=True,
        help="Status of the contract",
        default="draft",
    )

    def _gender_label(self):
        self.ensure_one()
        gender_mapping = {
            'male' : 'Nam',
            'female' : 'Nữ',
            'other' : 'Khác',
        }
        return gender_mapping.get(self.gender)
        # return dict(self._fields["gender"]._description_selection(self.env)).get(self.gender)

    # def action_print_contract_pdf(self):
    #     self.ensure_one()
    #     return self.env.ref(
    #         "hrm_contract.action_report_hrm_contract_draft_pdf"
    #     ).report_action(self)

    def action_submit_contract(self):
        for record in self:
            if record.state_hr_contract != "draft":
                raise UserError(_("Only contracts in draft state can be submitted."))
            record.state_hr_contract = "submitted"
        hr_groups = ["hr_contract.group_hr_contract_manager"]
        self.notify_hr(
            subject=f"Yêu cầu làm phê duyệt hợp đồng - {self.emp_name}",
            message=f"Nhân viên {self.emp_name} đã gửi yêu cầu làm phê duyệt hợp đồng",
            additional_hr_groups=hr_groups,
            priority="2",
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thành công",
                "message": "Đã gửi yêu cầu duyệt!",
                "type": "success",
                "sticky": False,
            },
        }

    def action_reject_contract(self):
        self.state_hr_contract = "rejected"
        self.notify_staff(
            message=f"Đã từ chối hợp đồng - {self.emp_name}",
            employee_id=self.employee_submit,
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thành công",
                "message": "Không duyệt hợp đồng",
                "type": "success",
                "sticky": False,
            },
        }

    def action_approve_contract(self):
        self.state_hr_contract = "approved"
        for record in self:
            # record.map_to_hr_contract()
            record.notify_staff(message=f"Đã phê duyệt hợp đồng - {self.emp_name}", employee_id=self.employee_submit)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thành công",
                "message": "Đã duyệt thành công!",
                "type": "success",
                "sticky": False,
            },
        }

    # def map_to_hr_contract(self):
    #     self.ensure_one()
    #     if self.state_hr_contract != "approved":
    #         raise UserError(_("Only approved contracts can be mapped to hr.contract."))
    #     HrContract = self.env["hr.contract"]
    #     existing_contract = HrContract.search(
    #         [("employee_id", "=", self.employee_id.id), ("state", "in", ["approved"])],
    #         limit=1,
    #     )
    #     if existing_contract:
    #         raise UserError(
    #             _(
    #                 "The employee already has an active contract. Cannot map to hr.contract."
    #             )
    #         )
    #     new_contract = HrContract.create(
    #         {
    #             "name": self.name,
    #             "employee_id": self.employee_id.id,
    #             "date_start": self.date_start,
    #             "date_end": self.date_end,
    #             "resource_calendar_id": self.resource_calendar_id.id,
    #             "structure_type_id": self.structure_type_id.id,
    #             "department_id": self.department_id.id,
    #             "job_id": self.job_id.id,
    #             "contract_type_id": self.contract_type_id.id,
    #             "wage": self.wage,
    #             "state": "draft",
    #         }
    #     )
