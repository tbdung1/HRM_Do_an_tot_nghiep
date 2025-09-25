# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmEmployeeUpdateRequest(models.Model):
    _name = 'hrm.employee.update.request'
    _description = "Employee Information Update Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "display_name"

    # Basic Information
    name = fields.Char("Reference", default=lambda self: _("New"))
    display_name = fields.Char(
        "Display Name", compute="_compute_display_name", store=True
    )
    employee_id = fields.Many2one(
        "hr.employee",
        "Employee",
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id,
        domain=lambda self: (
            "[('user_id', '=', uid)]"
        ),
        readonly=True
    )
    department_id = fields.Many2one(
        "hr.department", related="employee_id.department_id", store=True
    )
    request_date = fields.Date("Request Date", default=fields.Date.today, tracking=True)

    # Request Details
    description = fields.Text("Description/Reason")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "hrm_update_request_attachment_rel",
        "request_id",
        "attachment_id",
        string="Supporting Documents",
    )

    update_tax_identification_number = fields.Boolean("Update Tax ID")
    new_tax_identification_number = fields.Char("New Tax ID")
    current_tax_identification_number = fields.Char(
        "Current Tax ID", related="employee_id.tax_identification_number", readonly=True
    )

    update_health_insurance_number = fields.Boolean("Update Health Insurance")
    new_health_insurance_number = fields.Char("New Health Insurance Number")
    current_health_insurance_number = fields.Char(
        "Current Health Insurance",
        related="employee_id.health_insurance_number",
        readonly=True,
    )

    # Contact Information
    update_work_phone = fields.Boolean("Update Work Phone")
    new_work_phone = fields.Char("New Work Phone")
    current_work_phone = fields.Char(
        "Current Work Phone", related="employee_id.work_phone", readonly=True
    )

    update_work_email = fields.Boolean("Update Work Email")
    new_work_email = fields.Char("New Work Email")
    current_work_email = fields.Char(
        "Current Work Email", related="employee_id.work_email", readonly=True
    )

    # Health Information
    update_health_status = fields.Boolean("Update Health Status")
    new_health_status = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("fair", "Fair"),
            ("poor", "Poor"),
        ],
        string="New Health Status",
    )
    current_health_status = fields.Selection(
        related="employee_id.health_status", readonly=True
    )

    update_medical_history = fields.Boolean("Update Medical History")
    new_medical_history = fields.Text("New Medical History")
    current_medical_history = fields.Text(
        "Current Medical History", related="employee_id.medical_history", readonly=True
    )

    # Process Information
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        copy=False,
    )

    hr_manager_id = fields.Many2one(
        "hr.employee", "HR Manager", tracking=True, readonly=True
    )
    approval_date = fields.Datetime("Approval Date", readonly=True)
    rejection_reason = fields.Text("Rejection Reason", readonly=True)
    # Computed Fields
    has_changes = fields.Boolean(
        "Has Changes", compute="_compute_has_changes", store=True
    )
    attachment_count = fields.Integer(
        "Attachment Count", compute="_compute_attachment_count"
    )

    @api.depends("name", "employee_id")
    def _compute_display_name(self):
        for record in self:
            if record.name and record.name != _("New"):
                record.display_name = f"{record.name} - {record.employee_id.name}"
            else:
                record.display_name = f"Update Request - {record.employee_id.name}"

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    @api.depends(
        "update_tax_identification_number",
        "update_health_insurance_number",
        "update_work_phone",
        "update_work_email",
        "update_health_status",
        "update_medical_history",
    )
    def _compute_has_changes(self):
        for record in self:
            record.has_changes = any(
                [
                    record.update_tax_identification_number,
                    record.update_health_insurance_number,
                    record.update_work_phone,
                    record.update_work_email,
                    record.update_health_status,
                    record.update_medical_history,
                ]
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "hrm.employee.update.request"
                ) or _("New")

            if vals.get("hr_manager_id"):
                vals["hr_manager_id"] = self.env.user.employee_id.parent_id.id
        return super().create(vals_list)

    @api.constrains("update_tax_identification_number", "new_tax_identification_number")
    def _check_tax_id_update(self):
        for record in self:
            if (
                record.update_tax_identification_number
                and not record.new_tax_identification_number
            ):
                raise ValidationError(_("New Tax ID is required when updating Tax ID"))

    def action_submit(self):
        """EC01_01: Submit request for review"""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted"))
            if not record.has_changes:
                raise UserError(_("Please select at least one field to update"))

            record.state = "submitted"

    def action_approve(self):
        """EC01_02: Approve and update employee information"""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be approved"))
            if not self.env.user.has_group("hr.group_hr_user"):
                raise UserError(_("Only HR users can approve requests"))

            record.state = "approved"
            record.hr_manager_id = self.env.user.employee_id.parent_id.id
            record.approval_date = fields.Datetime.now()

            # Update employee information
            record._update_employee_data()

            # # Notify employee
            # if record.employee_id.user_id:
            #     record.message_post(
            #         body="Your information update request has been approved and processed.",
            #         subject="Request Approved",
            #         partner_ids=[record.employee_id.user_id.partner_id.id],
            #     )

    def action_reject(self):
        """Open reject wizard"""
        if not self.env.user.has_group("hr.group_hr_user"):
            raise UserError(_("Only HR users can reject requests"))
        for record in self:
            record.state = "rejected"

    def action_reset_to_draft(self):
        """Reset to draft state"""
        for record in self:
            if record.state not in ["submitted", "rejected"]:
                raise UserError(
                    _("Only submitted or rejected requests can be reset to draft")
                )
            record.state = "draft"

    def action_view_attachments(self):
        """View attachments"""
        return {
            "name": _("Supporting Documents"),
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "view_mode": "kanban,tree,form",
            "domain": [("id", "in", self.attachment_ids.ids)],
            "context": {"default_res_model": self._name, "default_res_id": self.id},
        }

    def _update_employee_data(self):
        """Update employee information after approval"""
        self.ensure_one()
        employee = self.employee_id

        update_vals = {}

        # Personal Information
        if self.update_tax_identification_number:
            update_vals["tax_identification_number"] = (
                self.new_tax_identification_number
            )
        if self.update_health_insurance_number:
            update_vals["health_insurance_number"] = self.new_health_insurance_number

        # Contact Information
        if self.update_work_phone:
            update_vals["work_phone"] = self.new_work_phone
        if self.update_work_email:
            update_vals["work_email"] = self.new_work_email

        # Health Information
        if self.update_health_status:
            update_vals["health_status"] = self.new_health_status
        if self.update_medical_history:
            update_vals["medical_history"] = self.new_medical_history

        if update_vals:
            employee.write(update_vals)

            # Log the update
            employee.message_post(
                body=f"Information updated through request: {self.name}",
                subject="Employee Information Updated",
            )

        # Process attachments as documents
        if self.attachment_ids:
            for attachment in self.attachment_ids:
                self.env["hrm.employee.document"].create(
                    {
                        "name": attachment.name,
                        "document_type": "other",
                        "document_file": attachment.datas,
                        "employee_id": employee.id,
                        "notes": f"Uploaded through update request {self.name}",
                    }
                )
