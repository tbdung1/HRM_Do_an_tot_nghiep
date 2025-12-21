# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrNotification(models.Model):
    _name = "hr.notification"
    _description = "HR Notification System"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char("Subject", required=True, tracking=True)
    description = fields.Text("Description", tracking=True)
    employee_id = fields.Many2one(
        "hr.employee",
        string="From Employee",
        default=lambda self: self.env.user.employee_id,
        tracking=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="From User",
        default=lambda self: self.env.user,
        tracking=True,
    )

    priority = fields.Selection(
        [("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Urgent")],
        default="1",
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )

    source_model = fields.Char(
        "Source Model", help="Model that triggered this notification"
    )
    source_record_id = fields.Integer(
        "Source Record ID", help="ID of the record that triggered this notification"
    )
    hr_channel_id = fields.Many2one("mail.channel", string="HR Channel")

    @api.model
    def get_hr_users(self, additional_groups=None):
        """Lấy tất cả users thuộc HR groups

        Args:
            additional_groups (list): Danh sách thêm các group XML IDs
        """
        hr_groups = [
            "hr.group_hr_user",  # HR Officer
            "hr.group_hr_manager",  # HR Manager
            "base.group_hr_manager",  # HR Manager (base)
        ]

        # Thêm các groups bổ sung nếu có
        if additional_groups:
            hr_groups = additional_groups[:]

        hr_users = self.env["res.users"]

        for group_xml_id in hr_groups:
            try:
                group = self.env.ref(group_xml_id, raise_if_not_found=False)
                if group:
                    hr_users |= group.users
            except Exception as e:
                _logger.warning(f"Could not find group {group_xml_id}: {e}")

        return hr_users

    @api.model
    def send_hr_notification_to_channels(
        self,
        subject,
        message_body,
        employee_id=None,
        priority="1",
        additional_hr_groups=None,
        source_model=None,
        source_record_id=None,
    ):
        try:
            # Tạo notification record
            notification_vals = {
                "name": subject,
                "description": message_body,
                "employee_id": employee_id or self.env.user.employee_id.id,
                "user_id": self.env.user.id,
                "priority": priority,
                "source_model": source_model,
                "source_record_id": source_record_id,
                "state": "sent", 
            }

            notification = self.create(notification_vals)
            # Lấy HR users
            hr_users = self.get_hr_users(additional_hr_groups)
            if not hr_users:
                _logger.warning("No HR users found to send notification")
                return notification
            # Gửi tin nhắn đến từng HR user qua channel riêng
            current_user_partner = self.env.user.partner_id

            for hr_user in hr_users:
                if hr_user.id != self.env.user.id:  # Không gửi cho chính mình
                    try:
                        # Tạo channel 1-1 giữa current user và HR user
                        hr_partner = hr_user.partner_id

                        chan_info = self.env["discuss.channel"].channel_get(
                            [hr_partner.id]
                        )
                        channel = self.env["discuss.channel"].browse(chan_info["id"])

                        # Format tin nhắn đẹp
                        formatted_message = self._format_channel_message(
                            subject, message_body, notification, employee_id
                        )

                        # Gửi tin nhắn
                        channel.with_context(mail_create_nosubscribe=True).message_post(
                            body=formatted_message,
                            author_id=current_user_partner.id,
                            message_type="comment",
                            subtype_xmlid="mail.mt_comment",
                        )

                        _logger.info(f"Sent HR notification to user: {hr_user.name}")

                    except Exception as e:
                        _logger.error(
                            f"Failed to send notification to HR user {hr_user.name}: {e}"
                        )

            return notification

        except Exception as e:
            _logger.error(f"Failed to send HR notification: {e}")
            return False

    def _format_channel_message(
        self, subject, message_body, notification, employee_id=None
    ):
        """Format tin nhắn cho channel"""
        employee = (
            self.env["hr.employee"].browse(employee_id)
            if employee_id
            else self.env.user.employee_id
        )
        employee_name = employee.name if employee else self.env.user.name
        department = (
            employee.department_id.name
            if employee and employee.department_id
            else "N/A"
        )

        current_time = fields.Datetime.now().strftime("%d/%m/%Y %H:%M")

        formatted_message = f"""
Thông báo HR mới
━━━━━━━━━━━━━━━━━━━━
Tiêu đề: {subject}
|  Từ: {employee_name}
|  Phòng ban: {department}
|  Thời gian: {current_time}

|  Nội dung:
{message_body}

"""

        return formatted_message

    @api.model
    def send_quick_hr_notification(
        self,
        subject,
        message,
        employee_id=None,
        additional_hr_groups=None,
    ):

        return self.send_hr_notification_to_channels(
            subject=subject,
            message_body=message,
            employee_id=employee_id,
            additional_hr_groups=additional_hr_groups,
        )


class HrNotificationMixin(models.AbstractModel):
    """
    Mixin để các model khác có thể dễ dàng gửi HR notifications
    """

    _name = "hr.notification.mixin"
    _description = "HR Notification Mixin"

    def notify_staff(self, message, employee_id):
        employee_partner = employee_id.user_id.partner_id
        hr_partner = self.env.user.partner_id
        chan_info = self.env["discuss.channel"].channel_get([employee_partner.id])
        channel = self.env["discuss.channel"].browse(chan_info["id"])
        
        channel.with_context(mail_create_nosubscribe=True).message_post(
            body=message,
            author_id=hr_partner.id,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

    def notify_hr(
        self,
        subject,
        message,
        priority="1",
        additional_hr_groups=None,
    ):

        employee_id = None

        # Tự động tìm employee_id nếu model có
        if hasattr(self, "employee_id") and self.employee_id:
            employee_id = self.employee_id.id
        elif hasattr(self, "user_id") and self.user_id and self.user_id.employee_id:
            employee_id = self.user_id.employee_id.id
        else:
            employee_id = (
                self.env.user.employee_id.id if self.env.user.employee_id else None
            )

        return self.env["hr.notification"].send_hr_notification_to_channels(
            subject=subject,
            message_body=message,
            employee_id=employee_id,
            priority=priority,
            additional_hr_groups=additional_hr_groups,
            source_model=self._name,
            source_record_id=self.id if hasattr(self, "id") else None,
        )
