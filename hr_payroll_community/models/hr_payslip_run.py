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
        
        # Chỉ gửi email cho payslip đã done
        payslips_to_send = self.slip_ids.filtered(lambda p: p.state == 'done')
        
        if not payslips_to_send:
            raise UserError(_("No confirmed payslips found. Please confirm payslips before sending emails."))
        
        sent_count = 0
        failed_count = 0
        
        # Lấy hoặc tạo email template
        template = self._get_or_create_email_template()
        
        for payslip in payslips_to_send:
            try:
                # Kiểm tra nhân viên có email không
                if not payslip.employee_id.work_email:
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(f"Employee {payslip.employee_id.name} has no email address")
                    failed_count += 1
                    continue
                
                # Gửi email sử dụng template
                template.send_mail(payslip.id, force_send=True, raise_exception=False)
                sent_count += 1
                
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error(f"Failed to send email to {payslip.employee_id.name}: {str(e)}")
                failed_count += 1
        
        # Hiển thị thông báo
        message = _("Email Sending Completed!\n\n")
        message += _("Successfully sent: %d emails\n") % sent_count
        if failed_count > 0:
            message += _("Failed: %d emails") % failed_count
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Email Sent'),
                'message': message,
                'type': 'success' if failed_count == 0 else 'warning',
                'sticky': False,
            }
        }
    
    def _get_or_create_email_template(self):
        """
        Lấy hoặc tạo email template cho payslip
        
        @return: mail.template record
        """
        # Tìm template có external ID
        template = self.env.ref('hr_payroll_community.email_template_payslip', raise_if_not_found=False)
        
        # Nếu không có, tạo mới
        if not template:
            # Tìm report payslip (nếu có)
            report = self.env['ir.actions.report'].search([
                ('model', '=', 'hr.payslip'),
                ('report_type', '=', 'qweb-pdf')
            ], limit=1)
            
            template_vals = {
                'name': 'Payslip Notification',
                'model_id': self.env['ir.model']._get('hr.payslip').id,
                'subject': 'Your Payslip for {{ object.date_from.strftime("%B %Y") }}',
                'email_from': '{{ user.email_formatted }}',
                'email_to': '{{ object.employee_id.work_email }}',
                'body_html': '''
                    <p>Dear {{ object.employee_id.name }},</p>
                    
                    <p>Please find attached your payslip for the period:</p>
                    <p><strong>From:</strong> {{ object.date_from.strftime("%d/%m/%Y") }}<br/>
                    <strong>To:</strong> {{ object.date_to.strftime("%d/%m/%Y") }}</p>
                    
                    <p><strong>Total Amount:</strong> {{ '{:,.0f}'.format(object.total_amount) }} VND</p>
                    
                    <p>If you have any questions, please contact HR department.</p>
                    
                    <p>Best regards,<br/>
                    HR Department</p>
                ''',
                'auto_delete': False,
            }
            
            # Thêm report nếu tìm thấy
            if report:
                template_vals['report_template_ids'] = [(4, report.id)]
            
            template = self.env['mail.template'].create(template_vals)
            
            # Tạo external ID cho template
            self.env['ir.model.data'].create({
                'name': 'email_template_payslip',
                'module': 'hr_payroll_community',
                'model': 'mail.template',
                'res_id': template.id,
            })
        
        return template
