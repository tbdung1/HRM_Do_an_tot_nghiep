# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrPayrollAdjustment(models.Model):
    _name = 'hr.payroll.adjustment'
    _description = 'Trợ cấp và Khấu trừ Lương'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Mã yêu cầu',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Phòng ban',
        related='employee_id.department_id',
        store=True,
        readonly=True
    )
    
    date = fields.Date(
        string='Ngày yêu cầu',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    adjustment_type = fields.Selection([
        ('bonus', 'Thưởng'),
        ('penalty', 'Phạt'),
    ], string='Loại', required=True, default='bonus', tracking=True)
    
    amount = fields.Float(
        string='Số tiền',
        required=True,
        tracking=True
    )
    
    reason = fields.Text(
        string='Lý do',
        required=True,
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Đã gửi'),
        ('approved', 'Đã duyệt'),
        ('refused', 'Từ chối'),
    ], string='Trạng thái', default='draft', tracking=True, copy=False)
    
    approved_by = fields.Many2one(
        'res.users',
        string='Người duyệt',
        readonly=True,
        tracking=True
    )
    
    approved_date = fields.Datetime(
        string='Ngày duyệt',
        readonly=True,
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        required=True,
        default=lambda self: self.env.company
    )
    
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Phiếu lương',
        readonly=True,
        help='Phiếu lương có sử dụng điều chỉnh này'
    )
    
    notes = fields.Text(string='Ghi chú')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.payroll.adjustment') or _('New')
        return super(HrPayrollAdjustment, self).create(vals)

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_('Số tiền phải lớn hơn 0!'))

    def action_submit(self):
        """Gửi yêu cầu để HR duyệt"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Chỉ có thể gửi yêu cầu ở trạng thái Nháp!'))
            record.write({'state': 'submitted'})
            record.message_post(body=_('Yêu cầu đã được gửi để duyệt'))

    def action_approve(self):
        """HR duyệt yêu cầu"""
        for record in self:
            if record.state != 'submitted':
                raise UserError(_('Chỉ có thể duyệt yêu cầu ở trạng thái Đã gửi!'))
            record.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now()
            })

    def action_refuse(self):
        """HR từ chối yêu cầu"""
        for record in self:
            if record.state != 'submitted':
                raise UserError(_('Chỉ có thể từ chối yêu cầu ở trạng thái Đã gửi!'))
            record.write({
                'state': 'refused',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now()
            })

    def action_set_to_draft(self):
        """Đưa về trạng thái nháp"""
        for record in self:
            if record.state not in ['refused', 'approved']:
                raise UserError(_('Không thể đưa về trạng thái nháp!'))
            record.write({
                'state': 'draft',
                'approved_by': False,
                'approved_date': False
            })

    def unlink(self):
        """Chỉ cho phép xóa ở trạng thái nháp"""
        for record in self:
            if record.state not in ['draft', 'refused']:
                raise UserError(_('Chỉ có thể xóa yêu cầu ở trạng thái Nháp hoặc Từ chối!'))
        return super(HrPayrollAdjustment, self).unlink()
