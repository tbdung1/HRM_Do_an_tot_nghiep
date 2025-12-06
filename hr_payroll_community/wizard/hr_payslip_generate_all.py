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
                
                # Gửi email sử dụng template
                template.send_mail(payslip.id, force_send=True, raise_exception=False)
                sent_count += 1
                _logger.info(f"Sent payslip email to {payslip.employee_id.name} ({payslip.employee_id.work_email})")
                
            except Exception as e:
                _logger.error(f"Failed to send email to {payslip.employee_id.name}: {str(e)}")
                failed_count += 1
        
        return sent_count, failed_count
    
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
