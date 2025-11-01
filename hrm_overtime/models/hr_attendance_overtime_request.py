# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import time

_logger = logging.getLogger(__name__)


class HrAttendanceOvertimeRequest(models.Model):
    _name = 'hr.attendance.overtime.request'
    _description = 'HrAttendanceOvertimeRequest'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True,
        index=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        related="employee_id.department_id",
        store=True,
        readonly=True,
    )
    manager_id = fields.Many2one(
        "hr.employee",
        string="Manager",
        related="employee_id.parent_id",
        store=True,
        readonly=True,
    )

    # Overtime Type Configuration
    overtime_type_id = fields.Many2one(
        "hr.overtime.type",
        string="Overtime Type",
        required=True,
        tracking=True,
        help="Defines the overtime category (Weekday/Weekend/Holiday) with coefficient and rules",
    )
    coefficient = fields.Float(
        string="Coefficient",
        related="overtime_type_id.coefficient",
        store=True,
        readonly=True,
        help="Multiplier for overtime hours calculation",
    )

    # Time Information
    date_start = fields.Datetime(
        string="Start Date & Time",
        required=True,
        tracking=True,
        default=fields.Datetime.now,
    )
    date_end = fields.Datetime(string="End Date & Time", required=True, tracking=True)
    duration = fields.Float(
        string="Duration (Hours)",
        compute="_compute_duration",
        store=True,
        readonly=True,
        help="Automatically calculated from Start and End datetime",
    )
    duration_compensated = fields.Float(
        string="Compensated Hours",
        compute="_compute_duration_compensated",
        store=True,
        readonly=True,
        help="Duration multiplied by coefficient",
    )

    # Request Details
    reason = fields.Text(
        string="Reason",
        required=True,
        tracking=True,
        help="Describe the reason for overtime work",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_overtime_request_attachment_rel",
        "request_id",
        "attachment_id",
        string="Attachments",
        help="Supporting documents or evidence for overtime request",
    )
    refusal_reason = fields.Text(
        string="Refusal Reason",
        readonly=True,
        copy=False
    )

    # State Management
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("manager_approved", "Manager Approved"),
            ("hr_approved", "HR Approved"),
            ("refused", "Refused"),
            ("done", "Done"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )

    compensation_method = fields.Selection(
        [("pay", "Payment")],  # Chỉ 1 option
        string="Compensation Method",
        required=True,
        default="pay",
        readonly=True,  # Không cho đổi
    )

    # attendance_ids = fields.Many2many(
    #     "hr.attendance",
    #     "hr_overtime_request_attendance_rel",
    #     "request_id",
    #     "attendance_id",
    #     string="Related Attendance Records",
    #     readonly=True,
    # )

    @api.depends("date_start", "date_end")
    def _compute_duration(self):
        """Tính thời lượng từ start và end"""
        for record in self:
            if record.date_start and record.date_end:
                delta = record.date_end - record.date_start
                record.duration = delta.total_seconds() / 3600.0
            else:
                record.duration = 0.0

    @api.depends("duration", "coefficient")
    def _compute_duration_compensated(self):
        """Tính giờ sau khi nhân hệ số"""
        for record in self:
            record.duration_compensated = record.duration * record.coefficient

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        """Kiểm tra logic ngày giờ"""
        for record in self:
            if record.date_end <= record.date_start:
                raise ValidationError(_("End time must be after start time!"))

            if record.duration < 0:
                raise ValidationError(_("Duration cannot be negative!"))

    @api.constrains("date_start", "date_end")
    def _check_overtime_hours(self):
        """
        Kiểm tra OT phải nằm NGOÀI giờ làm việc thông thường:
        - Sau 17:30
        - Trước 8:00 sáng hôm sau
        
        NOTE: Odoo lưu datetime dưới dạng UTC, cần convert về timezone của user
        """
        from datetime import time
        import pytz
        
        for record in self:
            # Lấy timezone của user hoặc company
            tz = pytz.timezone(self.env.user.tz or self.env.company.resource_calendar_id.tz or 'UTC')
            
            # Convert UTC sang timezone của user
            date_start_local = pytz.utc.localize(record.date_start).astimezone(tz)
            date_end_local = pytz.utc.localize(record.date_end).astimezone(tz)
            
            start_time = date_start_local.time()
            end_time = date_end_local.time()
            
            # Giờ làm việc thông thường: 8:00 - 17:30
            WORK_START = time(8, 0)  # 8:00
            WORK_END = time(17, 30)  # 17:30

            # Case 1: OT trong cùng ngày (VD: 18:00 - 21:00)
            if date_start_local.date() == date_end_local.date():
                # Phải bắt đầu sau 17:30
                if start_time < WORK_END:
                    raise ValidationError(
                        _("Overtime must start after 17:30!\n"
                        "Current start time: %s (Local time)")
                        % date_start_local.strftime("%Y-%m-%d %H:%M:%S")
                    )

            # Case 2: OT qua đêm (VD: 18:00 hôm nay - 2:00 sáng mai)
            else:
                # Ngày bắt đầu: phải sau 17:30
                if start_time < WORK_END:
                    raise ValidationError(
                        _("Overtime must start after 17:30!\n"
                        "Current start time: %s (Local time)")
                        % date_start_local.strftime("%Y-%m-%d %H:%M:%S")
                    )

                # Ngày kết thúc: phải trước 8:00
                if end_time > WORK_START:
                    raise ValidationError(
                        _("Overnight overtime must end before 08:00!\n"
                        "Current end time: %s (Local time)")
                        % date_end_local.strftime("%Y-%m-%d %H:%M:%S")
                    )

    @api.constrains("date_start", "date_end", "employee_id")
    def _check_overlapping_requests(self):
        """Kiểm tra không trùng request khác"""
        for record in self:
            if record.state in ["draft", "refused"]:
                continue

            overlapping = self.search(
                [
                    ("id", "!=", record.id),
                    ("employee_id", "=", record.employee_id.id),
                    ("state", "not in", ["draft", "refused"]),
                    ("date_start", "<", record.date_end),
                    ("date_end", ">", record.date_start),
                ]
            )

            if overlapping:
                raise ValidationError(
                    _(
                        "Overlapping overtime request found!\n"
                        "This employee already has another OT request in the same period."
                    )
                )

    def action_submit(self):
        """Nhân viên gửi yêu cầu"""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted!"))

            record.write({"state": "submitted"})

            # Tạo activity cho manager
            if record.manager_id and record.manager_id.user_id:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=record.manager_id.user_id.id,
                    summary=_("Overtime Request Approval"),
                    note=_(
                        f"Please review overtime request from {record.employee_id.name}"
                    ),
                )

            record.message_post(
                body=_("Overtime request submitted for approval"),
                subject=_("OT Request Submitted"),
            )

    def action_manager_approve(self):
        """Manager duyệt"""
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be approved!"))

            record.write(
                {
                    "state": "manager_approved",
                }
            )

            # Xóa activity của manager
            record.activity_unlink(["mail.mail_activity_data_todo"])

            # Tạo activity cho HR
            hr_users = self.env.ref("hr.group_hr_manager").users
            if hr_users:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=hr_users[0].id,
                    summary=_("Overtime Request - HR Approval"),
                    note=_(
                        f"Manager approved OT request from {record.employee_id.name}"
                    ),
                )

            record.message_post(
                body=_("Overtime request approved by manager"),
                subject=_("Manager Approved"),
            )

    def action_hr_approve(self):
        """HR duyệt - Kiểm tra presence trước khi duyệt"""
        for record in self:
            if record.state != "manager_approved":
                raise UserError(
                    _("Only manager-approved requests can be approved by HR!")
                )


            # Ghi vào hr.attendance.overtime
            record._create_overtime_record()

            record.write(
                {
                    "state": "hr_approved",
                }
            )

            # Xóa activity
            record.activity_unlink(["mail.mail_activity_data_todo"])

            record.message_post(
                body=_(
                    "Overtime request approved by HR. Overtime hours recorded for payroll."
                ),
                subject=_("HR Approved"),
            )

    def action_refuse(self):
        """Từ chối với lý do"""
        return {
            "name": _("Refuse Overtime Request"),
            "type": "ir.actions.act_window",
            "res_model": "hr.overtime.refuse.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_done(self):
        """Hoàn tất"""
        for record in self:
            if record.state != "hr_approved":
                raise UserError(_("Only HR-approved requests can be marked as done!"))

            record.write({"state": "done"})

            record.message_post(
                body=_("Overtime request completed"), subject=_("Completed")
            )

    def _create_overtime_record(self):
        """Tạo/cập nhật hr.attendance.overtime để tính lương"""
        self.ensure_one()

        date = self.date_start.date()
        overtime = self.env["hr.attendance.overtime"].search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("date", "=", date),
                ("adjustment", "=", False),
            ],
            limit=1,
        )

        if overtime:
            # Gộp vào record cùng ngày
            overtime.write(
                {
                    "duration": overtime.duration + self.duration_compensated,
                    "duration_real": overtime.duration_real + self.duration,
                }
            )
        else:
            # Tạo mới
            self.env["hr.attendance.overtime"].create(
                {
                    "employee_id": self.employee_id.id,
                    "date": date,
                    "duration": self.duration_compensated,  # Đã nhân hệ số
                    "duration_real": self.duration,  # Giờ thực
                    "adjustment": False,
                }
            )

    def unlink(self):
        """Không cho xóa request đã approve"""
        for record in self:
            if record.state not in ["draft", "refused"]:
                raise UserError(_("Cannot delete approved or submitted requests!"))
        return super(self).unlink()


class HrOvertimeType(models.Model):
    _name = "hr.overtime.type"
    _description = "Overtime Type"
    _order = "sequence, name"

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
        help="Overtime type name (e.g., Weekday, Weekend, Holiday)",
    )
    code = fields.Char(
        string="Code", required=True, help="Internal code for overtime type"
    )
    sequence = fields.Integer(string="Sequence", default=10, help="Display order")
    active = fields.Boolean(string="Active", default=True)

    coefficient = fields.Float(
        string="Coefficient",
        required=True,
        default=1.5,
        help="Multiplier for overtime hours (e.g., 1.5 = 150%, 2.0 = 200%)",
    )

    description = fields.Text(
        string="Description", help="Additional information about this overtime type"
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Overtime type code must be unique!")
    ]

    @api.constrains("coefficient")
    def _check_coefficient(self):
        """Validate coefficient value"""
        for record in self:
            if record.coefficient <= 0:
                raise ValidationError(_("Coefficient must be greater than 0!"))
