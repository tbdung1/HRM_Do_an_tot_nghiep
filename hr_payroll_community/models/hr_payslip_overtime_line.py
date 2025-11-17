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
#############################################################################
from odoo import api, fields, models


class HrPayslipOvertimeLine(models.Model):
    """Model for storing overtime information in payslip"""
    _name = 'hr.payslip.overtime.line'
    _description = 'Payslip Overtime Line'
    _order = 'payslip_id, sequence, date'

    name = fields.Char(string='Description', required=True,
                       help="Description for Overtime")
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip',
                                 required=True,
                                 ondelete='cascade', index=True,
                                 help="Payslip reference")
    sequence = fields.Integer(required=True, index=True, default=10,
                              string="Sequence",
                              help="Sequence for overtime lines")
    code = fields.Char(required=True, string="Code",
                       help="The code that can be used in the salary rules")
    date = fields.Date(string='Date', required=True,
                      help="Date of overtime")
    overtime_id = fields.Many2one('hr.overtime', string='Overtime Request',
                                  ondelete='set null',
                                  help="Reference to the overtime request")
    overtime_type_id = fields.Many2one('overtime.type', string='Overtime Type',
                                       ondelete='set null',
                                       help="Type of overtime")
    number_of_hours = fields.Float(string='Number of Hours',
                                   help="Number of overtime hours")
    rate = fields.Float(string='Rate', 
                       store=True,
                       help="Overtime rate/multiplier (e.g., 1.5 for 150%) from overtime type rules")
    amount = fields.Float(string='Amount',
                         compute='_compute_amount',
                         store=True,
                         help="Total overtime amount")
    contract_id = fields.Many2one('hr.contract', string='Contract',
                                  required=True,
                                  help="The contract for which this overtime applies")
    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  related='contract_id.employee_id',
                                  store=True,
                                  help="Employee reference")
    hourly_wage = fields.Float(string='Hourly Wage',
                              help="Base hourly wage for overtime calculation")



    @api.depends('number_of_hours', 'rate', 'hourly_wage')
    def _compute_amount(self):
        """
        Tính tổng tiền tăng ca:
        Amount = Số giờ × Rate × Lương theo giờ
        """
        for record in self:
            record.amount = record.number_of_hours * record.rate * record.hourly_wage
