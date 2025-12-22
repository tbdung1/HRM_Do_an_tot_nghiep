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
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import base64

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    """Create new model for getting Payslip Batches"""
    _name = 'hr.payslip.run'
    _description = 'Payslip Batches'

    name = fields.Char(required=True, help="Name for Payslip Batches",
                       string="Name")
    slip_ids = fields.One2many('hr.payslip',
                               'payslip_run_id',
                               string='Payslips',
                               help="Choose Payslips for Batches")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
                               help="Status for Payslip Batches")
    date_start = fields.Date(string='Date From', required=True,
                             help="start date for batch",
                             default=lambda self: fields.Date.to_string(
                                 date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True,
                           help="End date for batch",
                           default=lambda self: fields.Date.to_string(
                               (datetime.now() + relativedelta(months=+1, day=1,
                                                               days=-1)).date())
                           )
    credit_note = fields.Boolean(string='Credit Note',
                                 help="If its checked, indicates that all"
                                      "payslips generated from here are refund"
                                      "payslips.")
    is_validate = fields.Boolean(compute='_compute_is_validate')

    def _compute_is_validate(self):
        for record in self:
            if record.slip_ids and record.slip_ids.filtered(
                    lambda slip: slip.state == 'draft'):
                record.is_validate = True
            else:
                record.is_validate = False

    def action_validate_payslips(self):
        if self.slip_ids:
            for slip in self.slip_ids.filtered(
                    lambda slip: slip.state == 'draft'):
                slip.action_payslip_done()

    def action_payslip_run(self):
        """Function for state change"""
        return self.write({'state': 'draft'})

    def close_payslip_run(self):
        """Function for state change"""
        return self.write({'state': 'close'})

    def action_generate_all_payslips(self):
        """
        Tự động tạo bảng lương cho tất cả nhân viên có hợp đồng đang chạy
        """
        self.ensure_one()
        
        # Tìm tất cả hợp đồng active trong kỳ
        contracts = self.env['hr.contract'].search([
            ('state', '=', 'open'),
            ('date_start', '<=', self.date_end),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', self.date_start),
        ])
        
        employees = contracts.mapped('employee_id')
        
        if not employees:
            raise UserError(_("No employees found with active contracts in the selected period!"))
        
        # Tạo bảng lương cho từng nhân viên
        payslips = self.env['hr.payslip']
        created_count = 0
        skipped_count = 0
        
        for employee in employees:
            try:
                # Kiểm tra xem đã có payslip trong kỳ chưa
                existing_payslip = self.env['hr.payslip'].search([
                    ('employee_id', '=', employee.id),
                    ('date_from', '=', self.date_start),
                    ('date_to', '=', self.date_end),
                    ('state', '!=', 'cancel'),
                ], limit=1)
                
                if existing_payslip:
                    skipped_count += 1
                    continue
                
                # Lấy thông tin từ onchange_employee_id
                slip_data = self.env['hr.payslip'].onchange_employee_id(
                    self.date_start, 
                    self.date_end, 
                    employee.id, 
                    contract_id=False
                )
                
                # Chuẩn bị dữ liệu tạo payslip
                payslip_vals = {
                    'employee_id': employee.id,
                    'name': slip_data['value'].get('name'),
                    'struct_id': slip_data['value'].get('struct_id'),
                    'contract_id': slip_data['value'].get('contract_id'),
                    'date_from': self.date_start,
                    'date_to': self.date_end,
                    'company_id': employee.company_id.id,
                    'payslip_run_id': self.id,
                }
                
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
                
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error(f"Failed to create payslip for {employee.name}: {str(e)}")
                skipped_count += 1
                continue
        
        # Tính toán tất cả payslips
        if payslips:
            payslips.action_compute_sheet()
        
        # Hiển thị thông báo
        message = _("Payslips Generated Successfully!\\n\\n")
        message += _("Created: %d payslips\\n") % created_count
        if skipped_count > 0:
            message += _("Skipped: %d payslips (already exist or error)") % skipped_count
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_send_payslip_emails(self):
        """
        Gửi email phiếu lương cho tất cả nhân viên trong batch
        """
        self.ensure_one()
        
        if not self.slip_ids:
            raise UserError(_("No payslips found in this batch!"))
        
        # Kiểm tra cấu hình email server
        mail_server = self.env['ir.mail_server'].sudo().search([], limit=1)
        if not mail_server:
            raise UserError(_(
                "Email server is not configured!\n\n"
                "Please go to Settings > Technical > Email > Outgoing Mail Servers "
                "to configure your email server before sending emails."
            ))
        
        # Chỉ gửi email cho payslip đã done
        payslips_to_send = self.slip_ids.filtered(lambda p: p.state == 'done')
        
        if not payslips_to_send:
            raise UserError(_("No confirmed payslips found. Please confirm payslips before sending emails."))
        
        # Đảm bảo tất cả payslips đã được compute
        import logging
        _logger = logging.getLogger(__name__)
        
        for payslip in payslips_to_send:
            _logger.info(f"Payslip {payslip.number} - State: {payslip.state}, Lines: {len(payslip.line_ids)}")
            if not payslip.line_ids:
                _logger.warning(f"Payslip {payslip.number} for {payslip.employee_id.name} has no computed lines. Computing now...")
                payslip.compute_sheet()
                _logger.info(f"After compute: {len(payslip.line_ids)} lines")
            else:
                # Log một vài line để debug
                for line in payslip.line_ids[:3]:
                    _logger.info(f"  Line: {line.code} - {line.name} - Amount: {line.amount} - Total: {line.total}")
        
        sent_count = 0
        failed_count = 0
        no_email_count = 0
        failed_employees = []
        
        # Lấy hoặc tạo email template
        template = self._get_or_create_email_template()
        
        import logging
        _logger = logging.getLogger(__name__)
        
        for payslip in payslips_to_send:
            try:
                # Kiểm tra nhân viên có email không
                if not payslip.employee_id.work_email:
                    _logger.warning(f"Employee {payslip.employee_id.name} has no email address")
                    no_email_count += 1
                    failed_employees.append(f"{payslip.employee_id.name} (no email)")
                    continue
                
                # Validate email format
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, payslip.employee_id.work_email):
                    _logger.warning(f"Employee {payslip.employee_id.name} has invalid email: {payslip.employee_id.work_email}")
                    no_email_count += 1
                    failed_employees.append(f"{payslip.employee_id.name} (invalid email format)")
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
                    failed_employees.append(f"{payslip.employee_id.name} (failed to create mail)")
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
                    _logger.info(f"Successfully sent email to {payslip.employee_id.name} ({payslip.employee_id.work_email})")
                else:
                    failed_count += 1
                    # Lấy lý do lỗi từ mail record
                    error_msg = mail.failure_reason or f'Mail state: {mail.state}'
                    failed_employees.append(f"{payslip.employee_id.name} ({error_msg[:80]})")
                    _logger.error(f"Failed to send email to {payslip.employee_id.name} ({payslip.employee_id.work_email}): {error_msg}")
                
            except Exception as e:
                _logger.error(f"Failed to send email to {payslip.employee_id.name}: {str(e)}")
                failed_count += 1
                failed_employees.append(f"{payslip.employee_id.name} ({str(e)[:80]})")
        
        # Hiển thị thông báo chi tiết
        message = _("Email Sending Completed!\n\n")
        message += _("Successfully sent: %d emails\n") % sent_count
        
        if no_email_count > 0:
            message += _("No email address: %d employees\n") % no_email_count
        
        if failed_count > 0:
            message += _("Failed to send: %d emails\n") % failed_count
            if failed_employees and len(failed_employees) <= 10:
                message += _("\nFailed employees:\n")
                message += "\n".join([f"  - {emp}" for emp in failed_employees])
        
        # Xác định loại thông báo
        if sent_count > 0 and failed_count == 0 and no_email_count == 0:
            notification_type = 'success'
            title = _('Success')
        elif sent_count > 0:
            notification_type = 'warning'
            title = _('Partially Sent')
        else:
            notification_type = 'danger'
            title = _('Failed')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notification_type,
                'sticky': True,  # Hiển thị lâu hơn để user đọc
            }
        }
    
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
        import logging
        _logger = logging.getLogger(__name__)
        
        report = self.env.ref('hr_payroll_community.hr_payslip_new_report_action', raise_if_not_found=False)
        if not report:
            # Fallback: tìm report theo model
            report = self.env['ir.actions.report'].search([
                ('model', '=', 'hr.payslip'),
                ('report_name', '=', 'hr_payroll_community.report_payslip')
            ], limit=1)
        
        if report:
            _logger.info(f"Found report: {report.name} (ID: {report.id}, report_name: {report.report_name})")
        else:
            _logger.error("No payslip report found!")
        
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
            _logger.info(f"Added report {report.id} to template")
        
        template = self.env['mail.template'].create(template_vals)
        
        # Tạo external ID cho template
        self.env['ir.model.data'].create({
            'name': 'email_template_payslip',
            'module': 'hr_payroll_community',
            'model': 'mail.template',
            'res_id': template.id,
        })
        
        return template
