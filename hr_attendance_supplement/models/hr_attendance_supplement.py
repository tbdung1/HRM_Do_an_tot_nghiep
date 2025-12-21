from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time
import pytz

class HrmAttendanceSupplement(models.Model):
    _name = 'hr.attendance.supplement'
    _description = 'HRM Attendance Supplement'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one('hr.employee', string='Nhân viên', required=True, default=lambda self: self.env.user.employee_id)
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

    supplement_type = fields.Selection([
        ('full_day', 'Cả Ngày'),
        ('half_day', 'Nửa Ngày'),
    ], string='Loại', required=True, default='full_day', tracking=True)
    
    # Cho cả ngày
    date_from = fields.Date(string='Từ Ngày', tracking=True)
    date_to = fields.Date(string='Đến Ngày', tracking=True)
    
    # Cho nửa ngày
    single_date = fields.Date(string='Ngày', tracking=True)
    period = fields.Selection([
        ('morning', 'Sáng'),
        ('afternoon', 'Chiều'),
    ], string='Lựa Chọn', tracking=True)
    
    reason = fields.Text(string='Lý do bổ sung', required=True)
    attachment_ids = fields.Many2many('ir.attachment', 'hr_attendance_supplement_attachment_rel', 
                                      'supplement_id', 'attachment_id', 
                                      string='File đính kèm')
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Chờ phê duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    approved_by = fields.Many2one('res.users', string='Người duyệt', readonly=True)
    created_attendance_ids = fields.Many2many('hr.attendance', string='Bản ghi chấm công', readonly=True)
    attendance_count = fields.Integer(string='Số bản ghi', compute='_compute_attendance_count')

    @api.depends('created_attendance_ids')
    def _compute_attendance_count(self):
        for record in self:
            record.attendance_count = len(record.created_attendance_ids)

    @api.constrains('supplement_type', 'date_from', 'date_to', 'single_date', 'period')
    def _check_dates(self):
        for record in self:
            if record.supplement_type == 'full_day':
                if not record.date_from or not record.date_to:
                    raise ValidationError("Vui lòng chọn ngày bắt đầu và kết thúc cho loại Cả Ngày!")
                if record.date_to < record.date_from:
                    raise ValidationError("Ngày kết thúc phải sau ngày bắt đầu!")
            elif record.supplement_type == 'half_day':
                if not record.single_date:
                    raise ValidationError("Vui lòng chọn ngày cho loại Nửa Ngày!")
                if not record.period:
                    raise ValidationError("Vui lòng chọn Sáng hoặc Chiều!")

    @api.onchange('supplement_type')
    def _onchange_supplement_type(self):
        if self.supplement_type == 'full_day':
            self.single_date = False
            self.period = False
        elif self.supplement_type == 'half_day':
            self.date_from = False
            self.date_to = False

    def action_submit(self):
        for rec in self:
            # Kiểm tra xem người dùng hiện tại có phải là nhân viên của record không
            if rec.employee_id.user_id != self.env.user:
                raise ValidationError("Bạn không có quyền gửi yêu cầu này.")
            rec.state = 'submitted'
            rec.message_post(body="📤 Yêu cầu đã được gửi để phê duyệt.")

    def action_approve(self):
        """HR duyệt và tạo bản ghi attendance mới"""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError("Chỉ có thể duyệt yêu cầu ở trạng thái 'Chờ phê duyệt'.")
            
            created_attendances = []
            # Timezone Việt Nam
            vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            
            if rec.supplement_type == 'full_day':
                # Tạo attendance cho tất cả các ngày từ date_from đến date_to
                current_date = rec.date_from
                while current_date <= rec.date_to:
                    # Bỏ qua cuối tuần (Saturday = 5, Sunday = 6)
                    if current_date.weekday() < 5:  # Monday=0 to Friday=4
                        # Tạo datetime với timezone Việt Nam rồi chuyển sang UTC
                        check_in_local = vietnam_tz.localize(datetime.combine(current_date, time(8, 0)))
                        check_out_local = vietnam_tz.localize(datetime.combine(current_date, time(17, 0)))
                        check_in = check_in_local.astimezone(pytz.UTC).replace(tzinfo=None)
                        check_out = check_out_local.astimezone(pytz.UTC).replace(tzinfo=None)
                        
                        # Kiểm tra xem đã có attendance trong ngày này chưa
                        existing = self.env['hr.attendance'].search([
                            ('employee_id', '=', rec.employee_id.id),
                            ('check_in', '>=', datetime.combine(current_date, time(0, 0))),
                            ('check_in', '<', datetime.combine(current_date + timedelta(days=1), time(0, 0))),
                        ])
                        
                        if not existing:
                            attendance = self.env['hr.attendance'].create({
                                'employee_id': rec.employee_id.id,
                                'check_in': check_in,
                                'check_out': check_out,
                            })
                            created_attendances.append(attendance.id)
                    
                    current_date += timedelta(days=1)
            
            elif rec.supplement_type == 'half_day':
                # Tạo attendance cho nửa ngày
                if rec.period == 'morning':
                    check_in_local = vietnam_tz.localize(datetime.combine(rec.single_date, time(8, 0)))
                    check_out_local = vietnam_tz.localize(datetime.combine(rec.single_date, time(12, 0)))
                else:  # afternoon
                    check_in_local = vietnam_tz.localize(datetime.combine(rec.single_date, time(13, 0)))
                    check_out_local = vietnam_tz.localize(datetime.combine(rec.single_date, time(17, 0)))
                
                check_in = check_in_local.astimezone(pytz.UTC).replace(tzinfo=None)
                check_out = check_out_local.astimezone(pytz.UTC).replace(tzinfo=None)
                
                # Kiểm tra xem đã có attendance trong khoảng thời gian này chưa
                existing = self.env['hr.attendance'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    '|',
                    '&', ('check_in', '<=', check_in), ('check_out', '>=', check_in),
                    '&', ('check_in', '<=', check_out), ('check_out', '>=', check_out),
                ])
                
                if existing:
                    raise ValidationError(f"Đã tồn tại bản ghi chấm công trong khoảng thời gian này!")
                
                attendance = self.env['hr.attendance'].create({
                    'employee_id': rec.employee_id.id,
                    'check_in': check_in,
                    'check_out': check_out,
                })
                created_attendances.append(attendance.id)
            
            if not created_attendances:
                raise ValidationError("Không có bản ghi chấm công nào được tạo. Có thể đã tồn tại hoặc không có ngày làm việc trong khoảng thời gian đã chọn.")
            
            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'created_attendance_ids': [(6, 0, created_attendances)],
            })
            
            rec.message_post(body=f"✅ Yêu cầu đã được duyệt. Đã tạo {len(created_attendances)} bản ghi chấm công.")

    def action_reject(self):
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError("Chỉ có thể từ chối yêu cầu ở trạng thái 'Chờ phê duyệt'.")
            
            rec.state = 'rejected'
            rec.message_post(body="❌ Yêu cầu bị từ chối.")

    def action_view_attendance(self):
        """Xem bản ghi attendance đã tạo"""
        self.ensure_one()
        if not self.created_attendance_ids:
            raise ValidationError("Chưa có bản ghi chấm công nào được tạo.")
        
        return {
            'name': 'Bản ghi chấm công',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.created_attendance_ids.ids)],
            'target': 'current',
        }
