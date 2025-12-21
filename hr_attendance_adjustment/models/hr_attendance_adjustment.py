from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, time, timedelta

class HrmAttendanceAdjustment(models.Model):
    _name = 'hr.attendance.adjustment'
    _description = 'HRM Attendance Adjustment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    attendance_id = fields.Many2one('hr.attendance', string='Attendance Record', required=True)
    employee_id = fields.Many2one(related='attendance_id.employee_id', string='Employee', store=True, readonly=True)
    can_submit = fields.Boolean(compute='_compute_user_rights', store=False)
    can_approve = fields.Boolean(compute='_compute_user_rights', store=False)

    @api.depends('employee_id', 'state')
    def _compute_user_rights(self):
        for record in self:
            # Kiểm tra nếu người dùng hiện tại là nhân viên của record này
            is_employee = record.employee_id.user_id == self.env.user
            # Kiểm tra nếu người dùng là quản lý HR
            is_hr_manager = self.env.user.has_group('hr.group_hr_manager')
            
            # Nhân viên chỉ có thể submit khi là chủ record và record ở trạng thái draft
            record.can_submit = is_employee and record.state == 'draft'
            # HR manager có thể approve/reject khi record ở trạng thái submitted
            record.can_approve = is_hr_manager and record.state == 'submitted'
    check_in_new = fields.Datetime(string='New Check-In Time', required=True)
    check_out_new = fields.Datetime(string='New Check-Out Time', required=True)
    reason = fields.Text(string='Reason for Adjustment', required=True)
    adjustment_count = fields.Integer(string='Số yêu cầu', compute='_compute_adjustment_count')
    
    def _compute_adjustment_count(self):
        for record in self:
            count = self.search_count([
                ('attendance_id', '=', record.attendance_id.id),
                ('id', '!=', record.id)
            ])
            record.adjustment_count = count

    @api.onchange('check_in_new')
    def _onchange_check_in_new(self):
        if self.check_in_new and self.attendance_id.check_in:
            # Giữ nguyên ngày của attendance, chỉ thay đổi giờ
            self.check_in_new = self.check_in_new.replace(
                year=self.attendance_id.check_in.year,
                month=self.attendance_id.check_in.month,
                day=self.attendance_id.check_in.day
            )

    @api.onchange('check_out_new')
    def _onchange_check_out_new(self):
        if self.check_out_new and self.attendance_id.check_out:
            # Giữ nguyên ngày của attendance, chỉ thay đổi giờ
            self.check_out_new = self.check_out_new.replace(
                year=self.attendance_id.check_out.year,
                month=self.attendance_id.check_out.month,
                day=self.attendance_id.check_out.day
            )

    @api.onchange('attendance_id')
    def _onchange_attendance_id(self):
        if self.attendance_id:
            self.check_in_new = self.attendance_id.check_in
            self.check_out_new = self.attendance_id.check_out
    state = fields.Selection([
         ('draft', 'Draft'),
        ('submitted', 'Awaiting Approval'),
        ('manager_approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    update_by = fields.Many2one('res.users', string='Updated By')

    def action_submit(self):
        for rec in self:
            # Kiểm tra xem người dùng hiện tại có phải là nhân viên của record không
            if rec.employee_id.user_id != self.env.user:
                raise ValidationError("Bạn không có quyền gửi yêu cầu này.")
            rec.state = 'submitted'


    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            rec.message_post(body="❌ Yêu cầu bị từ chối.")

    def action_update_attendance(self):
        """HR cập nhật lại hr.attendance sau khi giám đốc BP duyệt"""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError("Chưa submit.")
            if rec.attendance_id:
                rec.attendance_id.write({
                    'check_in': rec.check_in_new,
                    'check_out': rec.check_out_new,
                })
            rec.update_by = self.env.user
            rec.state = 'manager_approved'
            rec.message_post(body="🛠 Đã cập nhật bảng công. Gửi lại cho nhân viên xác nhận.")

    def action_view_history(self):
        """Xem lịch sử các yêu cầu điều chỉnh của attendance này"""
        self.ensure_one()
        return {
            'name': 'Lịch sử điều chỉnh',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.adjustment',
            'view_mode': 'tree,form',
            'domain': [
                ('attendance_id', '=', self.attendance_id.id),
                ('id', '!=', self.id)
            ],
        }