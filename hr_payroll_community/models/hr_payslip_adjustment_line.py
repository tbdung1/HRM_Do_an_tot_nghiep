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


class HrPayslipAdjustmentLine(models.Model):
    """Model for storing payroll adjustment information in payslip"""
    _name = 'hr.payslip.adjustment.line'
    _description = 'Payslip Adjustment Line'
    _order = 'payslip_id, sequence, date'

    name = fields.Char(string='Description', required=True,
                       help="Description for Adjustment")
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip',
                                 required=True,
                                 ondelete='cascade', index=True,
                                 help="Payslip reference")
    sequence = fields.Integer(required=True, index=True, default=10,
                              string="Sequence",
                              help="Sequence for adjustment lines")
    code = fields.Char(required=True, string="Code",
                       help="The code that can be used in the salary rules")
    date = fields.Date(string='Date', required=True,
                      help="Date of adjustment")
    adjustment_id = fields.Many2one('hr.payroll.adjustment', string='Adjustment Request',
                                   ondelete='set null',
                                   help="Reference to the payroll adjustment request")
    adjustment_type = fields.Selection([
        ('bonus', 'Thưởng'),
        ('penalty', 'Phạt'),
    ], string='Loại', required=True,
                                      help="Type of adjustment: Bonus or Penalty")
    amount = fields.Float(string='Amount', required=True,
                         help="Adjustment amount")
    contract_id = fields.Many2one('hr.contract', string='Contract',
                                  required=True,
                                  help="The contract for which this adjustment applies")
    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  related='contract_id.employee_id',
                                  store=True,
                                  help="Employee reference")
