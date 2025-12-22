# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HrPayslipGenerateAll(models.TransientModel):
    """Wizard để tự động tạo bảng lương cho tất cả nhân viên có hợp đồng đang chạy"""
    _name = 'hr.payslip.generate.all'
    _description = 'Generate Payslips for All Active Employees'

    date_from = fields.Date(
        string='Date From', 
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
        help="Start date for payslip period"
    )
    date_to = fields.Date(
        string='Date To', 
        required=True,
        default=lambda self: (date.today().replace(day=1) + relativedelta(months=1, days=-1)),
        help="End date for payslip period"
    )
    create_batch = fields.Boolean(
        string='Create Payslip Batch',
        default=True,
        help="If checked, all payslips will be grouped in a batch"
    )
    batch_name = fields.Char(
        string='Batch Name',
        compute='_compute_batch_name',
        store=True,
        readonly=False,
        help="Name of the payslip batch"
    )
    employee_count = fields.Integer(
        string='Eligible Employees',
        compute='_compute_employee_count',
        help="Number of employees with active contracts in the period"
    )
    send_email = fields.Boolean(
        string='Send Email to Employees',
        default=False,
        help="If checked, payslip will be sent to employees via email"
    )

    @api.depends('date_from', 'date_to')
    def _compute_batch_name(self):
        """Tự động tạo tên batch từ kỳ lương"""
        for wizard in self:
            if wizard.date_from and wizard.date_to:
                wizard.batch_name = _("Payroll %s - %s") % (
                    wizard.date_from.strftime('%m/%Y'),
                    wizard.date_to.strftime('%m/%Y')
                )
            else:
                wizard.batch_name = _("Payroll Batch")

    @api.depends('date_from', 'date_to')
    def _compute_employee_count(self):
        """Tính số nhân viên đủ điều kiện"""
        for wizard in self:
            if wizard.date_from and wizard.date_to:
                employees = wizard._get_eligible_employees()
                wizard.employee_count = len(employees)
            else:
                wizard.employee_count = 0

    def _get_eligible_employees(self):
        """
        Lấy danh sách nhân viên có hợp đồng đang chạy trong kỳ
        """
        self.ensure_one()
        
        # Tìm tất cả hợp đồng active trong kỳ
        contracts = self.env['hr.contract'].search([
            ('state', '=', 'open'),
            ('date_start', '<=', self.date_to),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', self.date_from),
        ])
        
        # Lấy danh sách nhân viên từ các hợp đồng
        employees = contracts.mapped('employee_id')
        
        _logger.info(f"Found {len(employees)} employees with active contracts from {self.date_from} to {self.date_to}")
        
        return employees

    def action_generate_payslips(self):
        """
        Tạo bảng lương cho tất cả nhân viên có hợp đồng đang chạy
        """
        self.ensure_one()
        
        # Lấy danh sách nhân viên đủ điều kiện
        employees = self._get_eligible_employees()
        
        if not employees:
            raise UserError(_("No employees found with active contracts in the selected period!"))
        
        # Tạo batch nếu cần
        payslip_run = False
        if self.create_batch:
            payslip_run = self.env['hr.payslip.run'].create({
                'name': self.batch_name,
                'date_start': self.date_from,
                'date_end': self.date_to,
                'state': 'draft',
            })
            _logger.info(f"Created payslip batch: {self.batch_name}")
        
        # Tạo bảng lương cho từng nhân viên
        payslips = self.env['hr.payslip']
        created_count = 0
        skipped_count = 0
        
        for employee in employees:
            try:
                # Kiểm tra xem đã có payslip trong kỳ chưa
                existing_payslip = self.env['hr.payslip'].search([
                    ('employee_id', '=', employee.id),
                    ('date_from', '=', self.date_from),
                    ('date_to', '=', self.date_to),
                    ('state', '!=', 'cancel'),
                ], limit=1)
                
                if existing_payslip:
                    _logger.info(f"Payslip already exists for {employee.name}, skipping...")
                    skipped_count += 1
                    continue
                
                # Lấy thông tin từ onchange_employee_id
                slip_data = self.env['hr.payslip'].onchange_employee_id(
                    self.date_from, 
                    self.date_to, 
                    employee.id, 
                    contract_id=False
                )
                
                # Chuẩn bị dữ liệu tạo payslip
                payslip_vals = {
                    'employee_id': employee.id,
                    'name': slip_data['value'].get('name'),
                    'struct_id': slip_data['value'].get('struct_id'),
                    'contract_id': slip_data['value'].get('contract_id'),
                    'date_from': self.date_from,
                    'date_to': self.date_to,
                    'company_id': employee.company_id.id,
                }
                
                # Thêm batch nếu có
                if payslip_run:
                    payslip_vals['payslip_run_id'] = payslip_run.id
                
                # Thêm input lines và worked days lines
                if slip_data['value'].get('input_line_ids'):
                    payslip_vals['input_line_ids'] = [
                        (0, 0, x) for x in slip_data['value'].get('input_line_ids')
                    ]
                
                if slip_data['value'].get('worked_days_line_ids'):
                    payslip_vals['worked_days_line_ids'] = [
                        (0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')
                    ]
                
                # Tạo payslip
                payslip = self.env['hr.payslip'].create(payslip_vals)
                payslips += payslip
                created_count += 1
                
                _logger.info(f"Created payslip for {employee.name}")
                
            except Exception as e:
                _logger.error(f"Failed to create payslip for {employee.name}: {str(e)}")
                skipped_count += 1
                continue
        
        # Tính toán tất cả payslips
        if payslips:
            payslips.action_compute_sheet()
            _logger.info(f"Computed {len(payslips)} payslips")
        
        # Gửi email nếu được chọn
        email_sent_count = 0
        email_failed_count = 0
        if self.send_email and payslips:
            email_sent_count, email_failed_count = self._send_payslip_emails(payslips)
        
        # Hiển thị thông báo kết quả
        message = _("Payslips Generated Successfully!\n\n")
        message += _("Created: %d payslips\n") % created_count
        if skipped_count > 0:
            message += _("Skipped: %d payslips (already exist or error)\n") % skipped_count
        if self.send_email:
            message += _("\nEmail sent: %d\n") % email_sent_count
            if email_failed_count > 0:
                message += _("Email failed: %d\n") % email_failed_count
        
        # Quay về view phù hợp
        if payslip_run:
            # Quay về batch form
            return {
                'type': 'ir.actions.act_window',
                'name': _('Payslip Batch'),
                'res_model': 'hr.payslip.run',
                'res_id': payslip_run.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # Quay về danh sách payslips
            return {
                'type': 'ir.actions.act_window',
                'name': _('Generated Payslips'),
                'res_model': 'hr.payslip',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payslips.ids)],
                'target': 'current',
            }
    
    def _send_payslip_emails(self, payslips):
        """
        Gửi email phiếu lương cho nhân viên
        
        @param payslips: recordset của hr.payslip
        @return: tuple (sent_count, failed_count)
        """
        # Kiểm tra cấu hình email server
        mail_server = self.env['ir.mail_server'].sudo().search([], limit=1)
        if not mail_server:
            _logger.error("Email server is not configured!")
            return 0, len(payslips)
        
        # Đảm bảo tất cả payslips đã được compute
        for payslip in payslips:
            if not payslip.line_ids:
                _logger.warning(f"Payslip {payslip.number} for {payslip.employee_id.name} has no computed lines. Computing now...")
                payslip.compute_sheet()
        
        sent_count = 0
        failed_count = 0
        
        # Lấy hoặc tạo email template
        template = self._get_or_create_email_template()
        
        for payslip in payslips:
            try:
                # Kiểm tra nhân viên có email không
                if not payslip.employee_id.work_email:
                    _logger.warning(f"Employee {payslip.employee_id.name} has no email address")
                    failed_count += 1
                    continue
                
                # Validate email format
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, payslip.employee_id.work_email):
                    _logger.warning(f"Employee {payslip.employee_id.name} has invalid email: {payslip.employee_id.work_email}")
                    failed_count += 1
                    continue
                
                # Lấy email_from từ user hoặc company
                email_from = self.env.user.email_formatted or self.env.company.email or 'noreply@example.com'
                
                # Tạo body_html trực tiếp với dữ liệu thực tế
                date_from_str = payslip.date_from.strftime("%d/%m/%Y") if payslip.date_from else "N/A"
                date_to_str = payslip.date_to.strftime("%d/%m/%Y") if payslip.date_to else "N/A"
                total_amount_str = "{:,.0f}".format(payslip.total_amount or 0)
                
                body_html = f'''<div style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px;">
    <h2 style="color: #333;">Payslip Notification</h2>
    
    <p>Dear <strong>{payslip.employee_id.name}</strong>,</p>
    
    <p>Please find attached your payslip for the period:</p>
    
    <table style="width: 100%; margin: 20px 0; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background: #f9f9f9;"><strong>From:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{date_from_str}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background: #f9f9f9;"><strong>To:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{date_to_str}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background: #f9f9f9;"><strong>Net Salary:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd; color: #27ae60; font-size: 18px; font-weight: bold;">
                {total_amount_str} VND
            </td>
        </tr>
    </table>
    
    <p style="margin-top: 20px;">If you have any questions or concerns regarding your payslip, please don't hesitate to contact the HR department.</p>
    
    <p style="margin-top: 30px;">Best regards,<br/>
    <strong>HR Department</strong></p>
</div>'''
                
                # Tạo email - template sẽ tự động generate report PDF
                mail_id = template.send_mail(
                    payslip.id, 
                    force_send=False, 
                    raise_exception=False,
                    email_values={
                        'email_to': payslip.employee_id.work_email,
                        'email_from': email_from,
                        'body_html': body_html,
                        'recipient_ids': [],
                    }
                )
                
                if not mail_id:
                    failed_count += 1
                    _logger.error(f"Failed to create mail for {payslip.employee_id.name}")
                    continue
                
                # Lấy mail record
                mail = self.env['mail.mail'].sudo().browse(mail_id)
                
                # Đảm bảo email_to được set
                if not mail.email_to:
                    mail.write({'email_to': payslip.employee_id.work_email})
                
                _logger.info(f"Sending email to {payslip.employee_id.name} at {mail.email_to}")
                
                # Gửi email ngay lập tức
                try:
                    mail.send(raise_exception=False)
                    # Refresh để lấy state mới nhất
                    mail.invalidate_recordset(['state', 'failure_reason'])
                except Exception as send_error:
                    _logger.error(f"Error sending email to {payslip.employee_id.name}: {str(send_error)}")
                
                # Kiểm tra trạng thái sau khi gửi
                if mail.state == 'sent':
                    sent_count += 1
                    _logger.info(f"Sent payslip email to {payslip.employee_id.name} ({payslip.employee_id.work_email})")
                else:
                    failed_count += 1
                    error_msg = mail.failure_reason or f"Mail state is {mail.state}"
                    _logger.error(f"Failed to send email to {payslip.employee_id.name} ({payslip.employee_id.work_email}): {error_msg}")
                
            except Exception as e:
                _logger.error(f"Failed to send email to {payslip.employee_id.name}: {str(e)}")
                failed_count += 1
        
        return sent_count, failed_count
    
    def _get_or_create_email_template(self):
        """
        Lấy hoặc tạo email template cho payslip
        
        @return: mail.template record
        """
        # Xóa template cũ nếu có để tạo mới
        template = self.env.ref('hr_payroll_community.email_template_payslip', raise_if_not_found=False)
        if template:
            # Xóa external ID
            self.env['ir.model.data'].search([
                ('name', '=', 'email_template_payslip'),
                ('module', '=', 'hr_payroll_community'),
            ]).unlink()
            # Xóa template
            template.unlink()
        
        # Body HTML chuẩn
        body_html = '''<div style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px;">
    <h2 style="color: #333;">Payslip Notification</h2>
    
    <p>Dear <strong>{{ object.employee_id.name }}</strong>,</p>
    
    <p>Please find attached your payslip for the period:</p>
    
    <table style="width: 100%; margin: 20px 0; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background: #f9f9f9;"><strong>From:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{{ object.date_from.strftime("%d/%m/%Y") if object.date_from else "N/A" }}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background: #f9f9f9;"><strong>To:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{{ object.date_to.strftime("%d/%m/%Y") if object.date_to else "N/A" }}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background: #f9f9f9;"><strong>Net Salary:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd; color: #27ae60; font-size: 18px; font-weight: bold;">
                {{ "{:,.0f}".format(object.total_amount or 0) }} VND
            </td>
        </tr>
    </table>
    
    <p style="margin-top: 20px;">If you have any questions or concerns regarding your payslip, please don't hesitate to contact the HR department.</p>
    
    <p style="margin-top: 30px;">Best regards,<br/>
    <strong>HR Department</strong></p>
</div>'''
        
        # Nếu không có, tạo mới
        # Tìm report payslip chính xác
        report = self.env.ref('hr_payroll_community.hr_payslip_new_report_action', raise_if_not_found=False)
        if not report:
            # Fallback: tìm report theo model
            report = self.env['ir.actions.report'].search([
                ('model', '=', 'hr.payslip'),
                ('report_name', '=', 'hr_payroll_community.report_payslip')
            ], limit=1)
        
        template_vals = {
            'name': 'Payslip Notification',
            'model_id': self.env['ir.model']._get('hr.payslip').id,
            'subject': 'Your Payslip for {{ object.date_from.strftime("%B %Y") if object.date_from else "" }}',
            'body_html': body_html,
            'auto_delete': False,
        }
        
        # Thêm report nếu tìm thấy
        if report:
            template_vals['report_template_ids'] = [(6, 0, [report.id])]
        
        template = self.env['mail.template'].create(template_vals)
        
        # Tạo external ID cho template
        self.env['ir.model.data'].create({
            'name': 'email_template_payslip',
            'module': 'hr_payroll_community',
            'model': 'mail.template',
            'res_id': template.id,
        })
        
        return template
