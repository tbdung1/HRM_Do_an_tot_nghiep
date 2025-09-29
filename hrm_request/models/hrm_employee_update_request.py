# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmEmployeeUpdateRequest(models.Model):
    _name = "hrm.employee.update.request"
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
        domain=lambda self: ("[('user_id', '=', uid)]"),
        readonly=True,
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

    # Contact Information
    update_work_phone = fields.Boolean("Update Work Phone")
    new_work_phone = fields.Char("New Work Phone")
    current_work_phone = fields.Char(
        "Current Work Phone", related="employee_id.work_phone", readonly=True
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
        "hr.employee", "HR Manager", readonly=True
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
        "update_health_status",
    )
    def _compute_has_changes(self):
        for record in self:
            record.has_changes = any(
                [
                    record.update_health_status,
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

    def action_submit(self):
        """EC01_01: Submit request for review"""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted"))
            if not record.has_changes:
                raise UserError(_("Please select at least one field to update"))

            record.state = "submitted"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thành công",
                "message": "Yêu cầu cập nhật thông tin đã được gửi đi!",
                "type": "success",
                "sticky": False,
            },
        }

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

            record.message_post(
                body=f"""
                ✅ Yêu cầu cập nhật thông tin đã được duyệt
                    Người duyệt: {self.env.user.name}
                    Thời gian: {fields.Datetime.now().strftime('%d/%m/%Y %H:%M')}
                    Nhân viên: {record.employee_id.name}
                Thông tin nhân viên đã được cập nhật thành công.
            """,
                subject="Yêu cầu cập nhật thông tin đã được duyệt",
                subtype_xmlid="mail.mt_note",
            )

            if record.employee_id.user_id:
                updated_fields = record._get_updated_fields_summary()
                chat_message = f"✅ Yêu cầu cập nhật thông tin đã được duyệt - {record.name} | Người duyệt: {self.env.user.name} | Thời gian: {fields.Datetime.now().strftime('%d/%m/%Y %H:%M')} | {updated_fields}"

                # Tìm channel chính xác giữa HR User và Employee
                hr_partner = self.env.user.partner_id
                employee_partner = record.employee_id.user_id.partner_id

                chan_info = self.env['discuss.channel'].channel_get([employee_partner.id])
                channel = self.env['discuss.channel'].browse(chan_info['id'])

                # Gửi tin nhắn vào đúng channel này
                channel.with_context(mail_create_nosubscribe=True).message_post(
                    body=chat_message,
                    author_id=hr_partner.id,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thành công",
                "message": "Yêu cầu cập nhật thông tin đã được duyệt!",
                "type": "success",
                "sticky": False,
            },
        }

    def action_reject(self):
        """Open reject wizard"""
        if not self.env.user.has_group("hr.group_hr_user"):
            raise UserError(_("Only HR users can reject requests"))
        for record in self:
            record.state = "rejected"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thành công",
                "message": "Đã từ chối yêu cầu cập nhật thông tin!",
                "type": "success",
                "sticky": False,
            },
        }

    def action_reset_to_draft(self):
        """Reset to draft state"""
        for record in self:
            if record.state not in ["submitted", "rejected"]:
                raise UserError(
                    _("Only submitted or rejected requests can be reset to draft")
                )
            record.state = "draft"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thành công",
                "message": "Đã trở về trạng thái nháp!",
                "type": "success",
                "sticky": False,
            },
        }

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

    def _get_updated_fields_summary(self):
        """Tạo summary các trường đã được cập nhật"""
        self.ensure_one()
        updates = []

        if self.update_health_insurance_number:
            updates.append(f"• Số BHYT: {self.current_health_insurance_number or 'Trống'} → {self.new_health_insurance_number}")

        if self.update_work_phone:
            updates.append(f"• Điện thoại: {self.current_work_phone or 'Trống'} → {self.new_work_phone}")

        if self.update_work_email:
            updates.append(f"• Email công việc: {self.current_work_email or 'Trống'} → {self.new_work_email}")

        if self.update_health_status:
            status_selection = [
                ("excellent", "Excellent"),
                ("good", "Good"),
                ("fair", "Fair"),
                ("poor", "Poor"),
            ]
            status_dict = dict(status_selection)
            current_status = status_dict.get(self.current_health_status, 'Chưa cập nhật')
            new_status = status_dict.get(self.new_health_status, '')
            updates.append(f"• Tình trạng sức khỏe: {current_status} → {new_status}")

        if self.update_medical_history:
            updates.append(f"• Tiền sử bệnh: Đã cập nhật")

        return '\n'.join(updates) if updates else 'Không có thông tin cụ thể'

    def _update_employee_data(self):
        """Update employee information after approval"""
        self.ensure_one()
        employee = self.employee_id

        update_vals = {}

        # Personal Information
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
