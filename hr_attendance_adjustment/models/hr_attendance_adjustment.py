from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, time, timedelta

class HrmAttendanceAdjustment(models.Model):
    _name = 'hr.attendance.adjustment'
    _description = 'HRM Attendance Adjustment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    attendance_id = fields.Many2one('hr.attendance', string='Attendance Record', required=True)
    employee_id = fields.Many2one(related='attendance_id.employee_id', string='Employee', store=True, readonly=True)
    manager_id = fields.Many2one('res.users', string='Manager')
    check_in_new = fields.Datetime(string='New Check-In Time', required=True)
    check_out_new = fields.Datetime(string='New Check-Out Time', required=True) 
    reason = fields.Text(string='Reason for Adjustment', required=True)
    state = fields.Selection([
         ('draft', 'Nháp'),
        ('submitted', 'Đã gửi Giám đốc BP'),
        ('manager_approved', 'Đã duyệt bởi Giám đốc BP'),
        ('updated', 'Đã cập nhật bảng công'),
        ('employee_confirmed', 'Nhân viên xác nhận lại'),
        ('rejected', 'Từ chối'),
    ], string='Status', default='draft', tracking=True)
    update_by = fields.Many2one('res.users', string='Updated By')

    def action_submit(self):
        for rec in self:
            if not rec.manager_id:
                raise ValidationError("Bạn chưa chọn Giám đốc BP phê duyệt.")
            rec.state = 'submitted'
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=rec.manager_id.id,
                note=f"Yêu cầu điều chỉnh chấm công từ {rec.employee_id.name}"
            )

    def action_manager_approve(self):
        for rec in self:
            rec.state = 'manager_approved'
            rec.message_post(body="✅ Giám đốc BP đã duyệt yêu cầu.")

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            rec.message_post(body="❌ Yêu cầu bị từ chối.")

    def action_update_attendance(self):
        """HR cập nhật lại hr.attendance sau khi giám đốc BP duyệt"""
        for rec in self:
            if rec.state != 'manager_approved':
                raise ValidationError("Chỉ được cập nhật khi đã được duyệt.")
            if rec.attendance_id:
                rec.attendance_id.write({
                    'check_in': rec.check_in_new,
                    'check_out': rec.check_out_new,
                })
            rec.update_by = self.env.user
            rec.state = 'updated'
            rec.message_post(body="🛠 Đã cập nhật bảng công. Gửi lại cho nhân viên xác nhận.")
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=rec.employee_id.user_id.id,
                note="Bảng công của bạn đã được cập nhật. Vui lòng xác nhận lại."
            )

    def action_employee_confirm(self):
        for rec in self:
            rec.state = 'employee_confirmed'
            rec.message_post(body="✅ Nhân viên đã xác nhận bảng công sau điều chỉnh.")