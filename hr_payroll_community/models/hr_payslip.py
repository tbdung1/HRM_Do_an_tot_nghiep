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
from datetime import date, datetime, time
import babel
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

# This will generate 16th of days
ROUNDING_FACTOR = 16


class HrPayslip(models.Model):
    """Create new model for getting total Payroll Sheet for an Employee"""
    _name = 'hr.payslip'
    _inherit = 'mail.thread'
    _description = 'Pay Slip'

    struct_id = fields.Many2one(comodel_name='hr.payroll.structure',
                                string='Structure',
                                help='Defines the rules that have to be applied'
                                     ' to this payslip, accordingly '
                                     'to the contract chosen. If you let empty '
                                     'the field contract, this field isn\'t '
                                     'mandatory anymore and thus the rules '
                                     'applied will be all the rules set on the '
                                     'structure of all contracts of the '
                                     'employee valid for the chosen period')
    name = fields.Char(string='Payslip Name', help="Enter Payslip Name")
    number = fields.Char(string='Reference', copy=False,
                         help="References for Payslip", )
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee',
                                  required=True,
                                  help="Choose Employee for Payslip")
    date_from = fields.Date(string='Date From', required=True,
                            help="Start date for Payslip",
                            default=lambda self: fields.Date.to_string(
                                date.today().replace(day=1)))
    date_to = fields.Date(string='Date To', required=True,
                          help="End date for Payslip",
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1,
                                                              days=-1)).date()))
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, 
                the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    line_ids = fields.One2many('hr.payslip.line',
                               'slip_id',
                               string='Payslip Lines',
                               help="Choose Payslip for line")
    company_id = fields.Many2one('res.company', string='Company',
                                 copy=False, help="Choose Company for line",
                                 default=lambda self: self.env[
                                     'res.company']._company_default_get())
    worked_days_line_ids = fields.One2many('hr.payslip.worked.days',
                                           'payslip_id',
                                           string='Payslip Worked Days',
                                           copy=True,
                                           help="Payslip worked days for line")
    input_line_ids = fields.One2many('hr.payslip.input',
                                     'payslip_id',
                                     string='Payslip Inputs',
                                     help="Choose Payslip Input")
    overtime_line_ids = fields.One2many('hr.payslip.overtime.line',
                                        'payslip_id',
                                        string='Payslip Overtime Lines',
                                        copy=True,
                                        help="Overtime lines for this payslip with detailed information")
    adjustment_line_ids = fields.One2many('hr.payslip.adjustment.line',
                                         'payslip_id',
                                         string='Payslip Adjustment Lines',
                                         copy=True,
                                         help="Adjustment lines for this payslip (bonuses and penalties)")
    paid = fields.Boolean(string='Made Payment Order ? ',
                          copy=False, help="Is Payment Order")
    note = fields.Text(string='Internal Note', help="Description for Payslip")
    contract_id = fields.Many2one('hr.contract', string='Contract',
                                  help="Choose Contract for Payslip")
    details_by_salary_rule_category_ids = fields.One2many(
        comodel_name='hr.payslip.line',
        compute='_compute_details_by_salary_rule_category_ids',
        string='Details by Salary Rule Category', help="Details from the salary"
                                                       " rule category")
    credit_note = fields.Boolean(string='Credit Note',
                                 help="Indicates this payslip has "
                                      "a refund of another")
    payslip_run_id = fields.Many2one('hr.payslip.run',
                                     string='Payslip Batches',
                                     copy=False, help="Choose Payslip Run")
    payroll_batch_id = fields.Many2one('hr.payroll.batch',
                                       string='Bảng Lương Tháng',
                                       copy=False, 
                                       help="Bảng lương tháng chứa phiếu lương này",
                                       index=True)
    payslip_count = fields.Integer(compute='_compute_payslip_count',
                                   string="Payslip Computation Details",
                                   help="Set Payslip Count")
    total_amount = fields.Monetary(compute='_compute_total_amount',
                                   string="Total Salary",
                                   currency_field='currency_id',
                                   help="Total amount of all payslip lines")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='company_id.currency_id',
                                  readonly=True)

    def _compute_details_by_salary_rule_category_ids(self):
        """Compute function for Salary Rule Category for getting
         all Categories"""
        for payslip in self:
            payslip.details_by_salary_rule_category_ids = payslip.mapped(
                'line_ids').filtered(lambda line: line.category_id)

    def _compute_payslip_count(self):
        """Compute function for getting Total count of Payslips"""
        for payslip in self:
            payslip.payslip_count = len(payslip.line_ids)

    def _compute_total_amount(self):
        """Compute function for getting Total Salary Amount"""
        for payslip in self:
            # Sum of all totals from details_by_salary_rule_category_ids
            payslip.total_amount = sum(payslip.details_by_salary_rule_category_ids.mapped('total'))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Function for adding constrains for payslip datas
        by considering date_from and date_to fields"""
        if any(self.filtered(
                lambda payslip: payslip.date_from > payslip.date_to)):
            raise ValidationError(
                _("Payslip 'Date From' must be earlier 'Date To'."))

    def action_payslip_draft(self):
        """Function for change stage of Payslip"""
        return self.write({'state': 'draft'})

    def action_payslip_done(self):
        """Function for change stage of Payslip"""
        self.action_compute_sheet()
        return self.write({'state': 'done'})

    def action_payslip_cancel(self):
        """Function for change stage of Payslip"""
        return self.write({'state': 'cancel'})

    def action_refund_sheet(self):
        """Function for refund the Payslip sheet"""
        for payslip in self:
            copied_payslip = payslip.copy(
                {'credit_note': True, 'name': _('Refund: ') + payslip.name})
            copied_payslip.action_compute_sheet()
            copied_payslip.action_payslip_done()
        formview_ref = self.env.ref('hr_payroll_community.hr_payslip_view_form',
                                    False)
        treeview_ref = self.env.ref('hr_payroll_community.hr_payslip_view_tree',
                                    False)
        return {
            'name': _("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'),
                      (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }

    def unlink(self):
        """Function for unlink the Payslip"""
        if any(self.filtered(
                lambda payslip: payslip.state not in ('draft', 'cancel'))):
            raise UserError(
                _('You cannot delete a payslip which is not draft or cancelled!'
                  ))
        return super(HrPayslip, self).unlink()

    # TODO move this function into hr_contract module, on hr.employee object
    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: recordset of employee
        @param date_from: date_field
        @param date_to: date_field
        @return: returns the ids of all the contracts for the given employee
        that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to),
                    ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to),
                    ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the
        # date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|',
                    ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id),
                        ('state', '=', 'open'), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids

    def action_compute_sheet(self):
        """Function for compute Payslip sheet"""
        for payslip in self:
            number = payslip.number or self.env['ir.sequence'].next_by_code(
                'salary.slip')
            # delete old payslip lines
            payslip.line_ids.unlink()
            # delete old worked days lines
            payslip.worked_days_line_ids.unlink()
            # delete old overtime lines
            payslip.overtime_line_ids.unlink()
            # delete old adjustment lines
            payslip.adjustment_line_ids.unlink()
            
            # set the list of contract for which the rules have to be applied
            # if we don't give the contract, then the rules to apply should be
            # for all current contracts of the employee
            contract_ids = payslip.contract_id.ids or \
                           self.get_contract(payslip.employee_id,
                                             payslip.date_from, payslip.date_to)
            
            # Re-compute worked days
            contracts = self.env['hr.contract'].browse(contract_ids)
            worked_days_lines_data = self.get_worked_day_lines(contracts, payslip.date_from, payslip.date_to)
            worked_days_lines = [(0, 0, line) for line in worked_days_lines_data]
            
            # Re-compute overtime lines
            overtime_lines_data = self.get_overtime_lines(contracts, payslip.date_from, payslip.date_to)
            overtime_lines = [(0, 0, line) for line in overtime_lines_data]
            
            # Re-compute adjustment lines
            adjustment_lines_data = self.get_adjustment_lines(contracts, payslip.date_from, payslip.date_to)
            adjustment_lines = [(0, 0, line) for line in adjustment_lines_data]
            
            # Re-compute payslip lines - pass worked_days_lines_data, overtime_lines_data, and adjustment_lines_data
            lines = [(0, 0, line) for line in
                     self._get_payslip_lines(contract_ids, payslip.id, worked_days_lines_data, overtime_lines_data, adjustment_lines_data)]
            
            payslip.write({
                'line_ids': lines,
                'worked_days_line_ids': worked_days_lines,
                'overtime_line_ids': overtime_lines,
                'adjustment_line_ids': adjustment_lines,
                'number': number
            })
        return True

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contracts: Browse record of contracts, date_from, date_to
        @return: returns a list of dict containing the input that should be
        applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(
                lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from),
                                        time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to),
                                      time.max)
            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(
                day_from, day_to, calendar=contract.resource_calendar_id)
            multi_leaves = []
            for day, hours, leave in day_leave_intervals:
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if len(leave) > 1:
                    for each in leave:
                        if each.holiday_id:
                            multi_leaves.append(each.holiday_id)
                else:
                    holiday = leave.holiday_id
                    current_leave_struct = leaves.setdefault(
                        holiday.holiday_status_id, {
                            'name': holiday.holiday_status_id.name or _(
                                'Global Leaves'),
                            'sequence': 5,
                            'code': holiday.holiday_status_id.code or 'GLOBAL',
                            'number_of_days': 0.0,
                            'number_of_hours': 0.0,
                            'number_of_work_days': 0.0,
                            'contract_id': contract.id,
                        })
                    current_leave_struct['number_of_hours'] += hours
                    if work_hours:
                        current_leave_struct[
                            'number_of_days'] += hours / work_hours
            # compute worked days
            work_data = contract.employee_id.get_work_days_data(
                day_from, day_to, calendar=contract.resource_calendar_id)
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data['days'],  # Theo calendar
                'number_of_hours': work_data['hours'],
                'number_of_work_days': work_data.get('work_days', 0),  # Theo attendance
                'contract_id': contract.id,
            }
            res.append(attendances)
            uniq_leaves = [*set(multi_leaves)]
            c_leaves = {}
            for rec in uniq_leaves:
                duration = rec.duration_display.replace("days", "").strip()
                duration_in_hours = float(duration) * 24
                c_leaves.setdefault(rec.holiday_status_id,
                                    {'hours': duration_in_hours})
            for item in c_leaves:
                if not leaves or item not in leaves:
                    data = {
                        'name': item.name,
                        'sequence': 20,
                        'code': item.code or 'LEAVES',
                        'number_of_hours': c_leaves[item]['hours'],
                        'number_of_days': c_leaves[item][
                                              'hours'] / work_hours,
                        'number_of_work_days': 0.0,
                        'contract_id': contract.id,
                    }
                    res.append(data)
                for time_off in leaves:
                    if item == time_off:
                        leaves[item]['number_of_hours'] += c_leaves[item][
                            'hours']
                        leaves[item]['number_of_days'] \
                            += c_leaves[item]['hours'] / work_hours
            # ===== XỬ LÝ NGHỈ PHÉP: Chỉ hiển thị nghỉ phép đã duyệt được trả lương =====
            # KHÔNG extend leaves.values() ở đây nữa để tránh duplicate
            
            import logging
            _logger = logging.getLogger(__name__)
            
            if 'hr.leave' in self.env:
                # Lấy các ngày nghỉ phép đã được duyệt (state='validate')
                approved_leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', contract.employee_id.id),
                    ('state', '=', 'validate'),  
                    ('date_from', '<=', day_to),
                    ('date_to', '>=', day_from),
                ])
                
                _logger.info(f"=== APPROVED LEAVE DEBUG ===")
                _logger.info(f"Employee: {contract.employee_id.name}")
                _logger.info(f"Period: {date_from} to {date_to}")
                _logger.info(f"Found {len(approved_leaves)} approved leaves")
                
                # Nhóm các nghỉ phép theo loại (leave type)
                leave_by_type = {}
                for leave in approved_leaves:
                    leave_type = leave.holiday_status_id
                    
                    if leave_type.unpaid:
                        _logger.info(f"  - Skip unpaid leave: {leave.name}")
                        continue
                    
                    if leave_type not in leave_by_type:
                        leave_by_type[leave_type] = {
                            'days': 0.0,
                            'hours': 0.0,
                        }
                    
                    # Cộng dồn số ngày và giờ
                    leave_by_type[leave_type]['days'] += leave.number_of_days
                    leave_by_type[leave_type]['hours'] += leave.number_of_hours
                    
                    _logger.info(f"  - Leave: {leave.name}, Type: {leave_type.name}, "
                               f"Days: {leave.number_of_days}, Hours: {leave.number_of_hours}, "
                               f"State: {leave.state}")
                
                # Thêm vào kết quả - CHỈ các nghỉ phép đã duyệt được trả lương
                for leave_type, data in leave_by_type.items():
                    leave_line = {
                        'name': _("Paid Leave: %s") % leave_type.name,
                        'sequence': 15,  # Hiển thị sau WORK100 nhưng trước các loại leave khác
                        'code': f'LEAVE_{leave_type.code or leave_type.id}',
                        'number_of_days': data['days'],
                        'number_of_hours': data['hours'],
                        'number_of_work_days': data['days'],  # Tính như ngày làm việc
                        'contract_id': contract.id,
                    }
                    res.append(leave_line)
                    _logger.info(f"  Added paid leave line: {leave_type.name}, "
                               f"Days: {data['days']}, Hours: {data['hours']}")
            
        return res

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        """Function for getting contracts upon date_from and date_to fields"""
        res = []
        structure_ids = contracts.get_all_structures()
        rule_ids = self.env['hr.payroll.structure'].browse(
            structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in
                           sorted(rule_ids, key=lambda x: x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped(
            'input_ids')
        for contract in contracts:
            for input in inputs:
                input_data = {
                    'name': input.name,
                    'code': input.code,
                    'contract_id': contract.id,
                    'date_from': date_from,
                    'date_to': date_to,
                }
                res.append(input_data)
        return res

    @api.model
    def get_overtime_lines(self, contracts, date_from, date_to):
        """
        Get overtime lines for the given contracts and date range.
        Returns a list of overtime line data with date, hours, and rate information.
        
        @param contracts: Browse record of contracts
        @param date_from: Start date
        @param date_to: End date
        @return: List of dictionaries containing overtime line data
        """
        res = []
        
        # Check if hr.overtime model exists
        if 'hr.overtime' not in self.env:
            return res
        
        for contract in contracts:
            # Search for approved overtime requests in the period
            # More flexible search: match employee and period, contract can be empty or matching
            domain = [
                ('employee_id', '=', contract.employee_id.id),
                ('state', '=', 'approved'),
                '|',
                ('date_from', '>=', date_from),
                ('date_to', '>=', date_from),
            ]
            
            # Add date_to condition
            domain.extend([
                '|',
                ('date_from', '<=', date_to),
                ('date_to', '<=', date_to),
            ])
            
            overtime_requests = self.env['hr.overtime'].search(domain)
            
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"=== OVERTIME DEBUG ===")
            _logger.info(f"Employee: {contract.employee_id.name}")
            _logger.info(f"Contract: {contract.id}")
            _logger.info(f"Period: {date_from} to {date_to}")
            _logger.info(f"Found {len(overtime_requests)} overtime requests")
            
            for overtime in overtime_requests:
                _logger.info(f"  - OT: {overtime.name}, Date: {overtime.date_from} to {overtime.date_to}, Hours: {overtime.days_no_tmp}, State: {overtime.state}, test: {overtime.overtime_type_id}")
                
                # Calculate hourly wage from contract
                hourly_wage = 0.0
                if hasattr(contract, 'over_hour') and contract.over_hour:
                    hourly_wage = contract.over_hour
                elif contract.wage:
                    # Estimate hourly wage: monthly wage / (working hours per month)
                    # Assuming 22 working days * 8 hours = 176 hours per month
                    hourly_wage = contract.wage / 176.0
                
                # Get rate from overtime type rules
                rate = 1.0
                if overtime.overtime_type_id and overtime.overtime_type_id.rule_line_ids:
                    for rule in overtime.overtime_type_id.rule_line_ids:
                        _logger.info(f"Test 1:  {rule.hrs_amount}")
                        if rule.from_hrs <= overtime.days_no_tmp <= rule.to_hrs:
                            rate = rule.hrs_amount / 100
                            _logger.info(f"Rate:  {rate}")
                            break
                
                # Create overtime line data
                overtime_line_data = {
                    'name': overtime.name or 'Overtime',
                    'sequence': 20,
                    'code': 'OT',
                    'date': overtime.date_from.date() if overtime.date_from else date_from,
                    'number_of_hours': overtime.days_no_tmp if overtime.duration_type == 'hours' else overtime.days_no_tmp * 8,
                    'rate': rate,
                    'hourly_wage': hourly_wage,
                    'contract_id': contract.id,
                }
                
                # Set overtime_id if exists
                if overtime and overtime.id:
                    overtime_line_data['overtime_id'] = overtime.id
                
                res.append(overtime_line_data)
                _logger.info(f"  Added overtime line: hours={overtime_line_data['number_of_hours']}, rate will be computed, wage={hourly_wage}")
        
        return res

    @api.model
    def get_adjustment_lines(self, contracts, date_from, date_to):
        """
        Get adjustment lines (bonus/penalty) for the given contracts and date range.
        Returns a list of adjustment line data.
        
        @param contracts: Browse record of contracts
        @param date_from: Start date
        @param date_to: End date
        @return: List of dictionaries containing adjustment line data
        """
        res = []
        
        # Check if hr.payroll.adjustment model exists
        if 'hr.payroll.adjustment' not in self.env:
            return res
        
        for contract in contracts:
            # Search for approved adjustment requests in the period
            domain = [
                ('employee_id', '=', contract.employee_id.id),
                ('state', '=', 'approved'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ]
            
            adjustment_requests = self.env['hr.payroll.adjustment'].search(domain)
            
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"=== ADJUSTMENT DEBUG ===")
            _logger.info(f"Employee: {contract.employee_id.name}")
            _logger.info(f"Contract: {contract.id}")
            _logger.info(f"Period: {date_from} to {date_to}")
            _logger.info(f"Found {len(adjustment_requests)} adjustment requests")
            
            for adjustment in adjustment_requests:
                _logger.info(f"  - Adjustment: {adjustment.name}, Date: {adjustment.date}, Amount: {adjustment.amount}, Type: {adjustment.adjustment_type}, State: {adjustment.state}")
                
                # Determine code based on adjustment type
                code = 'BONUS' if adjustment.adjustment_type == 'bonus' else 'PENALTY'
                
                # Create adjustment line data
                adjustment_line_data = {
                    'name': adjustment.reason or adjustment.name,
                    'sequence': 30,
                    'code': code,
                    'date': adjustment.date,
                    'adjustment_type': adjustment.adjustment_type,
                    'amount': adjustment.amount,
                    'contract_id': contract.id,
                }
                
                # Set adjustment_id if exists
                if adjustment and adjustment.id:
                    adjustment_line_data['adjustment_id'] = adjustment.id
                
                res.append(adjustment_line_data)
                _logger.info(f"  Added adjustment line: amount={adjustment_line_data['amount']}, type={adjustment_line_data['adjustment_type']}")
        
        return res

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id, worked_days_lines_data=None, overtime_lines_data=None, adjustment_lines_data=None):
        """Function for getting Payslip Lines"""

        def _sum_salary_rule_category(localdict, category, amount):
            """Function for getting total sum of Salary Rule Category"""
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict,
                                                      category.parent_id,
                                                      amount)
            localdict['categories'].dict[category.code] \
                = category.code in localdict[
                'categories'].dict and localdict['categories'].dict[
                category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            """Class for Browsable Object"""

            def __init__(self, employee_id, dict, env):
                """Function for getting employee_id,dict and env"""
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                """Function for return dict value or record object"""
                # Tránh infinite recursion với các attribute đặc biệt
                if attr in ('employee_id', 'dict', 'env'):
                    return object.__getattribute__(self, attr)
                return self.dict.get(attr, 0.0)

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                 from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = 
                    pi.payslip_id AND pi.code = %s""",
                                    (
                                        self.employee_id, from_date, to_date,
                                        code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDaysLine(object):
            """Wrapper to access worked days fields - NO CACHING, direct access"""
            def __init__(self, record):
                self._record = record
            
            def __getattr__(self, attr):
                """Get attribute directly from record each time"""
                if attr == '_record':
                    return object.__getattribute__(self, '_record')
                
                record = object.__getattribute__(self, '_record')
                if not record:
                    return 0.0
                
                # Direct field access from recordset
                if attr in ('number_of_days', 'number_of_work_days', 'number_of_hours'):
                    try:
                        value = getattr(record, attr)
                        return float(value) if value else 0.0
                    except:
                        return 0.0
                
                return 0.0
            
            def __bool__(self):
                record = object.__getattribute__(self, '_record')
                return bool(record)
            
            __nonzero__ = __bool__

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def __getattr__(self, attr):
                """
                Override to return a wrapper object that provides access to record attributes
                """
                # Let BrowsableObject handle these
                if attr in ('employee_id', 'dict', 'env'):
                    return BrowsableObject.__getattribute__(self, attr)
                
                # Get dict using object.__getattribute__ to avoid recursion
                try:
                    worked_days_dict = object.__getattribute__(self, 'dict')
                except AttributeError:
                    return WorkedDaysLine(None)
                
                # Get the record from dict
                record = worked_days_dict.get(attr, None) if worked_days_dict else None
                
                # Return a wrapper that caches the field values
                return WorkedDaysLine(record)

            def _sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip days with respect to
                 from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_days) as number_of_days, 
                    sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = 
                    pi.payslip_id AND pi.code = %s""",
                                    (
                                        self.employee_id, from_date, to_date,
                                        code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                 from_date,to_date fields"""
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip hours with respect to
                 from_date,to_date fields"""
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class OvertimeLine(object):
            """Wrapper to access overtime line fields"""
            def __init__(self, record):
                self._record = record
            
            def __getattr__(self, attr):
                """Get attribute directly from record"""
                if attr == '_record':
                    return object.__getattribute__(self, '_record')
                
                record = object.__getattribute__(self, '_record')
                if not record:
                    return 0.0
                
                # Direct field access from recordset
                if attr in ('number_of_hours', 'rate', 'amount', 'hourly_wage'):
                    try:
                        value = getattr(record, attr)
                        return float(value) if value else 0.0
                    except:
                        return 0.0
                
                return 0.0
            
            def __bool__(self):
                record = object.__getattribute__(self, '_record')
                return bool(record)
            
            __nonzero__ = __bool__

        class Overtime(BrowsableObject):
            """Class for accessing overtime data in salary rules"""

            def __getattr__(self, attr):
                """
                Override to return a wrapper object that provides access to overtime record attributes
                """
                # Let BrowsableObject handle these
                if attr in ('employee_id', 'dict', 'env'):
                    return BrowsableObject.__getattribute__(self, attr)
                
                # Get dict using object.__getattribute__ to avoid recursion
                try:
                    overtime_dict = object.__getattribute__(self, 'dict')
                except AttributeError:
                    return OvertimeLine(None)
                
                # Get the record from dict
                record = overtime_dict.get(attr, None) if overtime_dict else None
                
                # Return a wrapper
                return OvertimeLine(record)

            def _sum(self, code, from_date, to_date=None):
                """Function for getting sum of overtime hours and amount"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_hours) as number_of_hours, 
                    sum(amount) as amount
                    FROM hr_payslip as hp, hr_payslip_overtime_line as pol
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = 
                    pol.payslip_id AND pol.code = %s""",
                                    (
                                        self.employee_id, from_date, to_date,
                                        code))
                return self.env.cr.fetchone()

            def sum_hours(self, code, from_date, to_date=None):
                """Function for getting sum of overtime hours"""
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_amount(self, code, from_date, to_date=None):
                """Function for getting sum of overtime amount"""
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class AdjustmentLine(object):
            """Wrapper to access adjustment line fields"""
            def __init__(self, record):
                self._record = record
            
            def __getattr__(self, attr):
                """Get attribute directly from record"""
                if attr == '_record':
                    return object.__getattribute__(self, '_record')
                
                record = object.__getattribute__(self, '_record')
                if not record:
                    return 0.0
                
                # Direct field access from recordset
                if attr in ('amount', 'adjustment_type'):
                    try:
                        value = getattr(record, attr)
                        if attr == 'amount':
                            return float(value) if value else 0.0
                        return value
                    except:
                        return 0.0 if attr == 'amount' else ''
                
                return 0.0
            
            def __bool__(self):
                record = object.__getattribute__(self, '_record')
                return bool(record)
            
            __nonzero__ = __bool__

        class Adjustment(BrowsableObject):
            """Class for accessing adjustment data in salary rules"""

            def __getattr__(self, attr):
                """
                Override to return a wrapper object that provides access to adjustment record attributes
                """
                # Let BrowsableObject handle these
                if attr in ('employee_id', 'dict', 'env'):
                    return BrowsableObject.__getattribute__(self, attr)
                
                # Get dict using object.__getattribute__ to avoid recursion
                try:
                    adjustment_dict = object.__getattribute__(self, 'dict')
                except AttributeError:
                    return AdjustmentLine(None)
                
                # Get the record from dict
                record = adjustment_dict.get(attr, None) if adjustment_dict else None
                
                # Return a wrapper
                return AdjustmentLine(record)

            def _sum(self, code, from_date, to_date=None):
                """Function for getting sum of adjustment amount"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as amount
                    FROM hr_payslip as hp, hr_payslip_adjustment_line as pal
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = 
                    pal.payslip_id AND pal.code = %s""",
                                    (
                                        self.employee_id, from_date, to_date,
                                        code))
                return self.env.cr.fetchone()

            def sum_amount(self, code, from_date, to_date=None):
                """Function for getting sum of adjustment amount"""
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for
            usability purposes"""

            def sum(self, code, from_date, to_date=None):
                """Function for getting sum of Payslip with respect to
                 from_date,to_date fields"""
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = 
                False then (pl.total) else (-pl.total) end)
                FROM hr_payslip as hp, hr_payslip_line as pl
                WHERE hp.employee_id = %s AND hp.state = 'done'
                AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id 
                = pl.slip_id AND pl.code = %s""",
                                    (
                                        self.employee_id, from_date, to_date,
                                        code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        # we keep a dict with the result because a value can be overwritten
        # by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        overtime_dict = {}
        adjustment_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        
        # Build worked_days_dict from passed data or from payslip
        if worked_days_lines_data:
            # Create temporary recordset from dict data for computation
            WorkedDaysModel = self.env['hr.payslip.worked.days']
            for wd_data in worked_days_lines_data:
                # Create a new record (not saved to DB) for computation
                temp_record = WorkedDaysModel.new(wd_data)
                worked_days_dict[wd_data.get('code')] = temp_record
        else:
            # Fallback to existing worked days
            for worked_days_line in payslip.worked_days_line_ids:
                worked_days_dict[worked_days_line.code] = worked_days_line
        
        # Build overtime_dict from passed data or from payslip
        if overtime_lines_data:
            # Create simple wrapper objects from dict data for computation
            class SimpleOvertimeLine:
                """Simple wrapper for overtime line data"""
                def __init__(self, data):
                    self.name = data.get('name', '')
                    self.code = data.get('code', 'OT')
                    self.date = data.get('date')
                    self.number_of_hours = float(data.get('number_of_hours', 0.0))
                    self.rate = float(data.get('rate', 1.0))
                    self.hourly_wage = float(data.get('hourly_wage', 0.0))
                    self.amount = self.number_of_hours * self.rate * self.hourly_wage
                    self.contract_id = data.get('contract_id')
                    self.overtime_id = data.get('overtime_id')
                    self.id = False  # Not saved to DB yet
            
            # Group overtime lines by code and aggregate
            from collections import defaultdict
            code_groups = defaultdict(list)
            
            for ot_data in overtime_lines_data:
                wrapper = SimpleOvertimeLine(ot_data)
                code_groups[ot_data.get('code')].append(wrapper)
            
            # Create aggregated wrapper for each code
            class AggregatedOvertimeLine:
                """Aggregated overtime line for multiple entries with same code"""
                def __init__(self, lines):
                    self.lines = lines
                    self.code = lines[0].code if lines else 'OT'
                    self.number_of_hours = sum(line.number_of_hours for line in lines)
                    self.amount = sum(line.amount for line in lines)
                    # For rate and hourly_wage, use weighted average or first line's values
                    if self.number_of_hours > 0:
                        self.rate = sum(line.rate * line.number_of_hours for line in lines) / self.number_of_hours
                        self.hourly_wage = sum(line.hourly_wage * line.number_of_hours for line in lines) / self.number_of_hours
                    else:
                        self.rate = lines[0].rate if lines else 1.0
                        self.hourly_wage = lines[0].hourly_wage if lines else 0.0
                    self.id = False
            
            for code, lines in code_groups.items():
                overtime_dict[code] = AggregatedOvertimeLine(lines)
                
        elif hasattr(payslip, 'overtime_line_ids'):
            # Fallback to existing overtime lines - also need to aggregate
            from collections import defaultdict
            code_groups = defaultdict(list)
            
            for overtime_line in payslip.overtime_line_ids:
                code_groups[overtime_line.code].append(overtime_line)
            
            # Create aggregated wrapper for database records
            class AggregatedOvertimeLineDB:
                """Aggregated overtime line for multiple DB records with same code"""
                def __init__(self, lines):
                    self.lines = lines
                    self.code = lines[0].code if lines else 'OT'
                    self.number_of_hours = sum(line.number_of_hours for line in lines)
                    self.amount = sum(line.amount for line in lines)
                    if self.number_of_hours > 0:
                        self.rate = sum(line.rate * line.number_of_hours for line in lines) / self.number_of_hours
                        self.hourly_wage = sum(line.hourly_wage * line.number_of_hours for line in lines) / self.number_of_hours
                    else:
                        self.rate = lines[0].rate if lines else 1.0
                        self.hourly_wage = lines[0].hourly_wage if lines else 0.0
                    self.id = False
            
            for code, lines in code_groups.items():
                overtime_dict[code] = AggregatedOvertimeLineDB(lines)
        
        # Build adjustment_dict from passed data or from payslip
        if adjustment_lines_data:
            # Create wrapper for dict data
            class SimpleAdjustmentLine:
                """Wrapper for adjustment data from dict"""
                def __init__(self, data):
                    self.code = data.get('code', 'BONUS')
                    self.adjustment_type = data.get('adjustment_type', 'bonus')
                    self.amount = float(data.get('amount', 0.0))
                    self.contract_id = data.get('contract_id')
                    self.adjustment_id = data.get('adjustment_id')
                    self.id = False  # Not saved to DB yet
            
            # Group adjustment lines by code and aggregate
            from collections import defaultdict
            code_groups = defaultdict(list)
            
            for adj_data in adjustment_lines_data:
                wrapper = SimpleAdjustmentLine(adj_data)
                code_groups[adj_data.get('code')].append(wrapper)
            
            # Create aggregated wrapper for each code
            class AggregatedAdjustmentLine:
                """Aggregated adjustment line for multiple entries with same code"""
                def __init__(self, lines):
                    self.lines = lines
                    self.code = lines[0].code if lines else 'BONUS'
                    self.adjustment_type = lines[0].adjustment_type if lines else 'bonus'
                    self.amount = sum(line.amount for line in lines)
                    self.id = False
            
            for code, lines in code_groups.items():
                adjustment_dict[code] = AggregatedAdjustmentLine(lines)
                
        elif hasattr(payslip, 'adjustment_line_ids'):
            # Fallback to existing adjustment lines - also need to aggregate
            from collections import defaultdict
            code_groups = defaultdict(list)
            
            for adjustment_line in payslip.adjustment_line_ids:
                code_groups[adjustment_line.code].append(adjustment_line)
            
            # Create aggregated wrapper for database records
            class AggregatedAdjustmentLineDB:
                """Aggregated adjustment line for multiple DB records with same code"""
                def __init__(self, lines):
                    self.lines = lines
                    self.code = lines[0].code if lines else 'BONUS'
                    self.adjustment_type = lines[0].adjustment_type if lines else 'bonus'
                    self.amount = sum(line.amount for line in lines)
                    self.id = False
            
            for code, lines in code_groups.items():
                adjustment_dict[code] = AggregatedAdjustmentLineDB(lines)
        
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line
        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict,
                                 self.env)
        overtime = Overtime(payslip.employee_id.id, overtime_dict, self.env)
        adjustment = Adjustment(payslip.employee_id.id, adjustment_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)
        baselocaldict = {'categories': categories, 'rules': rules,
                         'payslip': payslips, 'worked_days': worked_days,
                         'inputs': inputs, 'overtime': overtime, 'adjustment': adjustment, 'payslip_obj': payslip}
        # get the ids of the structures on the contracts and their
        # parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(
                set(payslip.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        # get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(
            structure_ids).get_all_rules()
        # run the rules by sequence
        sorted_rule_ids = [id for id, sequence in
                           sorted(rule_ids, key=lambda x: x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)
        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee,
                             contract=contract)
            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                # check if the rule can be applied
                if rule._satisfy_condition(
                        localdict) and rule.id not in blacklist:
                    # compute the amount of the rule
                    amount, qty, rate = rule._compute_rule(localdict)
                    # check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[
                        rule.code] or 0.0
                    # set/overwrite the amount computed for this rule in
                    # the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = _sum_salary_rule_category(
                        localdict, rule.category_id, tot_rule - previous_amount)
                    # create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }
                else:
                    # blacklist this rule and its children
                    blacklist += [id for id, seq in
                                  rule._recursive_search_of_rules()]
        return list(result_dict.values())

    # YTI
    # TODO To rename. This method is not really an onchange,
    #  as it is not in any view
    # employee_id and contract_id could be browse records
    def onchange_employee_id(self, date_from, date_to, employee_id=False,
                             contract_id=False):
        """Function for return worked days when changing onchange_employee_id"""
        # defaults
        res = {
            'value': {
                'line_ids': [],
                # delete old input lines
                'input_line_ids': [(2, x,) for x in self.input_line_ids.ids],
                # delete old worked days lines
                'worked_days_line_ids': [(2, x,) for x in
                                         self.worked_days_line_ids.ids],
                # 'details_by_salary_head':[], TODO put me back
                'name': '',
                'contract_id': False,
                'struct_id': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        employee = self.env['hr.employee'].browse(employee_id)
        locale = self.env.context.get('lang') or 'en_US'
        res['value'].update({
            'name': _('Salary Slip of %s for %s') % (
                employee.name, tools.ustr(
                    babel.dates.format_date(date=ttyme, format='MMMM-y',
                                            locale=locale))),
            'company_id': employee.company_id.id,
        })
        if not self.env.context.get('contract'):
            # fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                # set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                # if we don't give the contract, then the input to fill
                # should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)
        if not contract_ids:
            return res
        contract = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        struct = contract.struct_id
        if not struct:
            return res
        res['value'].update({
            'struct_id': struct.id,
        })
        # computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res

    @api.onchange('employee_id', )
    def onchange_employee(self):
        """Function for getting contract for employee"""
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
        locale = self.env.context.get('lang') or 'en_US'
        self.name = _('Salary Slip of %s for %s') % (
            employee.name, tools.ustr(
                babel.dates.format_date(date=ttyme, format='MMMM-y',
                                        locale=locale)))
        self.company_id = employee.company_id
        if not self.env.context.get('contract') or not self.contract_id:
            contract_ids = self.get_contract(employee, date_from, date_to)
            if not contract_ids:
                return
            self.contract_id = self.env['hr.contract'].browse(contract_ids[0])
        if not self.contract_id.struct_id:
            return
        self.struct_id = self.contract_id.struct_id
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        return

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        """Function for getting structure when changing contract"""
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        return

    def get_salary_line_total(self, code):
        """Function for getting total salary line"""
        self.ensure_one()
        line = self.line_ids.filtered(lambda line: line.code == code)
        if line:
            return line[0].total
        else:
            return 0.0

    @api.onchange('date_from')
    def onchange_date_from(self):
        """Function for getting contract for employee"""
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # # computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        if self.line_ids.search([('name', '=', 'Meal Voucher')]):
            self.line_ids.search(
                [('name', '=', 'Meal Voucher')]).salary_rule_id.write(
                {'quantity': self.worked_days_line_ids.number_of_days})
        return

    @api.onchange('date_to')
    def onchange_date_to(self):
        """Function for getting contract for employee"""
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []
        if self.contract_id:
            contract_ids = self.contract_id.ids
        # computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from,
                                                         date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(contracts, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        if self.line_ids.search([('name', '=', 'Meal Voucher')]):
            self.line_ids.search(
                [('name', '=', 'Meal Voucher')]).salary_rule_id.write(
                {'quantity': self.worked_days_line_ids.number_of_days})
        return
