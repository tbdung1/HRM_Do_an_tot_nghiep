# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmEmployeeUpdateRequest(models.Model):
    _name = "hrm.employee.update.request"
    _description = "Employee Information Update Request"
    _inherit = ["mail.thread", "mail.activity.mixin", "hr.notification.mixin"]
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
        readonly=True,
    )

    user_id = fields.Many2one(
        "res.users",
        "User",
        required=True,
        tracking=True,
        default=lambda self: self.env.user,
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
    update_private_email = fields.Boolean("Update Private Email")
    new_private_email = fields.Char("New Private Email")
    current_private_email = fields.Char(
        "Current Private Email",
        related="user_id.private_email",
        readonly=True,
    )

    update_private_phone = fields.Boolean("Update Private Phone")
    new_private_phone = fields.Char("New Private Phone")
    current_private_phone = fields.Char(
        "Current Private Phone",
        related="user_id.private_phone",
        readonly=True,
    )

    update_employee_bank_account = fields.Boolean("Update Bank Account")
    new_employee_bank_account_id = fields.Many2one(
        "res.partner.bank",
        "New Bank Account",
        domain="[('partner_id', '=', employee_id)]",
    )
    current_employee_bank_account_id = fields.Many2one(
        "res.partner.bank",
        "Current Bank Account",
        related="user_id.employee_bank_account_id",
        readonly=True,
    )

    update_private_street = fields.Boolean("Update Private Street")
    new_private_street = fields.Char("New Private Street")
    current_private_street = fields.Char(
        "Current Private Street",
        related="user_id.private_street",
        readonly=True,
    )

    update_private_street2 = fields.Boolean("Update Private Street 2")
    new_private_street2 = fields.Char("New Private Street 2")
    current_private_street2 = fields.Char(
        "Current Private Street 2",
        related="user_id.private_street2",
        readonly=True,
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
        related="user_id.health_status", readonly=True
    )

    update_km_home_work = fields.Boolean("Update Distance Home-Work")
    new_km_home_work = fields.Integer("New Distance (KM)")
    current_km_home_work = fields.Integer(
        "Current Distance (KM)", related="user_id.km_home_work", readonly=True
    )

    update_children = fields.Boolean("Update Number of Children")
    new_children = fields.Integer("New Number of Children")
    current_children = fields.Integer(
        "Current Number of Children", related="user_id.children", readonly=True
    )

    update_marital = fields.Boolean("Update Marital Status")
    new_marital = fields.Selection(
        [
            ("single", "Single"),
            ("married", "Married"),
            ("cohabitant", "Legal Cohabitant"),
            ("widower", "Widower"),
            ("divorced", "Divorced"),
        ],
        string="New Marital Status",
    )
    current_marital = fields.Selection(related="user_id.marital", readonly=True)

    update_emergency_contact = fields.Boolean("Update Emergency Contact")
    new_emergency_contact = fields.Char("New Emergency Contact")
    current_emergency_contact = fields.Char(
        "Current Emergency Contact",
        related="user_id.emergency_contact",
        readonly=True,
    )

    update_emergency_phone = fields.Boolean("Update Emergency Phone")
    new_emergency_phone = fields.Char("New Emergency Phone")
    current_emergency_phone = fields.Char(
        "Current Emergency Phone", related="user_id.emergency_phone", readonly=True
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

    department_id = fields.Many2one(
        "hr.department", "Department", readonly=True, related="employee_id.department_id"
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
        "update_private_email",
        "update_private_phone",
        "update_employee_bank_account",
        "update_km_home_work",
        "update_marital",
        "update_children",
        "update_health_status",
        "attachment_ids",
        "update_private_street",
        "update_private_street2",
    )
    def _compute_has_changes(self):
        for record in self:
            record.has_changes = any(
                [
                    record.update_private_email,
                    record.update_private_phone,
                    record.update_employee_bank_account,
                    record.update_km_home_work,
                    record.update_marital,
                    record.update_children,
                    record.update_health_status,
                    record.update_private_street,
                    record.update_private_street2,
                    len(record.attachment_ids) > 0,
                ]
            )

    @api.model
    def default_get(self, fields_list):
        """Override để set default values khi mở view"""
        res = super().default_get(fields_list)

        current_user = self.env.user
        current_employee = current_user.employee_id

        _logger.info(f"Default get - User: {current_user.name}, Employee: {current_employee.name if current_employee else 'None'}")

        # Set default cho employee_id
        if 'employee_id' in fields_list:
            if current_employee:
                res['employee_id'] = current_employee.id
            else:
                res['employee_id'] = self._default_employee()

        # Set default cho user_id
        if 'user_id' in fields_list:
            res['user_id'] = current_user.id

        return res

    def _default_employee(self):
        user = self.env.user
        # Ưu tiên employee đúng theo các công ty đang hoạt động (multi-company safe)
        emp = self.env['hr.employee'].search([
            ('user_id', '=', user.id),
            # ('company_id', 'in', self.env.companies.ids),
        ], limit=1)
        return emp.id

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
            self.notify_hr(
                subject=_("Yêu cầu chỉnh sửa hồ sơ - %s") % self.employee_id.name,
                message=_("Nhân viên %s đã gửi yêu cầu chỉnh sửa hồ sơ") % self.employee_id.name,
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thành công",
                "message": "Yêu cầu cập nhật thông tin đã được gửi đi!",
                "type": "success",
                "sticky": True,
                "next": {"type": "ir.actions.act_window_close"},
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
            if record.employee_id.user_id:
                message = (
                    _(
                        "Yêu cầu chỉnh sửa hồ sơ đã được duyệt - %s | Người duyệt: %s | Thời gian: %s"
                    )
                    % (
                        record.name,
                        self.env.user.name,
                        fields.Datetime.now().strftime('%d/%m/%Y %H:%M')
                    )
                )
                self.notify_staff(message=message, employee_id=record.employee_id)

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
            if record.employee_id.user_id:
                message = _(
                    "Yêu cầu chỉnh sửa hồ sơ đã bị từ chối - %s | Người từ chối: %s | Thời gian: %s"
                ) % (
                    record.name,
                    self.env.user.name,
                    fields.Datetime.now().strftime("%d/%m/%Y %H:%M"),
                )
                self.notify_staff(message=message, employee_id=record.employee_id)

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
            "context": {"default_res_model": self._name, "default_res_id": self.id, "create": False,},
        }

    def _get_updated_fields_summary(self):
        """Tạo summary các trường đã được cập nhật"""
        self.ensure_one()
        updates = []

        # Address updates
        if self.update_private_street:
            updates.append(
                f"• Địa chỉ: {self.current_private_street or 'Trống'} → {self.new_private_street}"
            )

        if self.update_private_street2:
            updates.append(
                f"• Địa chỉ 2: {self.current_private_street2 or 'Trống'} → {self.new_private_street2}"
            )

        if self.update_private_email:
            updates.append(
                f"• Email: {self.current_private_email or 'Trống'} → {self.new_private_email}"
            )

        if self.update_private_phone:
            updates.append(
                f"• Điện thoại: {self.current_private_phone or 'Trống'} → {self.new_private_phone}"
            )

        if self.update_employee_bank_account:
            current_bank = (
                self.current_employee_bank_account_id.acc_number
                if self.current_employee_bank_account_id
                else "Trống"
            )
            new_bank = (
                self.new_employee_bank_account_id.acc_number
                if self.new_employee_bank_account_id
                else "Trống"
            )
            updates.append(f"• Tài khoản ngân hàng: {current_bank} → {new_bank}")

        if self.update_km_home_work:
            updates.append(
                f"• Khoảng cách nhà - công ty: {self.current_km_home_work or 0} km → {self.new_km_home_work} km"
            )

        if self.update_marital:
            marital_dict = dict(self._fields["new_marital"].selection)
            current_marital = marital_dict.get(self.current_marital, "Chưa cập nhật")
            new_marital = marital_dict.get(self.new_marital, "")
            updates.append(f"• Tình trạng hôn nhân: {current_marital} → {new_marital}")

        if self.update_health_status:
            status_selection = [
                ("excellent", "Excellent"),
                ("good", "Good"),
                ("fair", "Fair"),
                ("poor", "Poor"),
            ]
            status_dict = dict(status_selection)
            current_status = status_dict.get(self.current_health_status, "Chưa cập nhật")
            new_status = status_dict.get(self.new_health_status, "")
            updates.append(f"• Tình trạng sức khỏe: {current_status} → {new_status}")

        if self.update_children:
            updates.append(
                f"• Số con: {self.current_children or 0} → {self.new_children}"
            )

        if self.attachment_ids:
            attachment_names = [att.name for att in self.attachment_ids]
            updates.append(f"• Tài liệu đính kèm: {', '.join(attachment_names)}")

        return "\n".join(updates) if updates else "Không có thông tin cụ thể"

    def _update_employee_data(self):
        """Update employee information after approval"""
        self.ensure_one()
        employee = self.employee_id
        user = employee.user_id

        user_update_vals = {}

        if self.update_private_street:
            user_update_vals["private_street"] = self.new_private_street
        if self.update_private_street2:
            user_update_vals["private_street2"] = self.new_private_street2
        if self.update_private_email:
            user_update_vals["private_email"] = self.new_private_email
        if self.update_private_phone:
            user_update_vals["private_phone"] = self.new_private_phone
        if self.update_employee_bank_account:
            user_update_vals["employee_bank_account_id"] = self.new_employee_bank_account_id
        if self.update_km_home_work:
            user_update_vals["km_home_work"] = self.new_km_home_work
        if self.update_marital:
            user_update_vals["marital"] = self.new_marital
        if self.update_children:
            user_update_vals["children"] = self.new_children
        if self.update_emergency_contact:
            user_update_vals["emergency_contact"] = self.new_emergency_contact
        if self.update_emergency_phone:
            user_update_vals["emergency_phone"] = self.new_emergency_phone
        if self.update_health_status:
            user_update_vals["health_status"] = self.new_health_status

        if user_update_vals and user:
            user.write(user_update_vals)

        if self.attachment_ids:
            for attachment in self.attachment_ids:
                # Update attachment để liên kết với employee
                attachment.write({
                    'res_model': 'hr.employee',
                    'res_id': employee.id,
                    'name': f"[{self.name}] {attachment.name}",  # Prefix với request number
                })
