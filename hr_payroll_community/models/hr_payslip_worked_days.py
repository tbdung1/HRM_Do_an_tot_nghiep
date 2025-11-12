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


class HrPayslipWorkedDays(models.Model):
    """Create new model for adding some fields"""
    _name = 'hr.payslip.worked.days'
    _description = 'Payslip Worked Days'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Description', required=True,
                       help="Description for Worked Days")
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip',
                                 required=True,
                                 ondelete='cascade', index=True,
                                 help="Choose Payslip for worked days")
    sequence = fields.Integer(required=True, index=True, default=10,
                              string="Sequence",
                              help="Sequence for worked days")
    code = fields.Char(required=True, string="Code",
                       help="The code that can be used in the salary rules")
    number_of_days = fields.Float(string='Number of Days',
                                  help="Number of days based on working schedule calendar")
    number_of_hours = fields.Float(string='Number of Hours',
                                   help="Number of hours worked")
    number_of_work_days = fields.Float(string='Actual Work Days',
                                       help="Number of actual work days based on attendance records")
    contract_id = fields.Many2one('hr.contract', string='Contract',
                                  required=True,
                                  help="The contract for which applied"
                                       "this input")
    hourly_rate = fields.Float(string='Hourly Rate', 
                               compute='_compute_hourly_rate',
                               store=True,
                               help="Hourly rate calculated from contract wage and number of hours")

    @api.depends('contract_id.wage', 'number_of_hours')
    def _compute_hourly_rate(self):
        """
        Tính lương 1 giờ dựa trên:
        - Lương trong hợp đồng (contract.wage)
        - Số giờ làm việc trong tháng (number_of_hours)
        
        Công thức: Lương 1 giờ = Lương hợp đồng / Số giờ làm việc
        """
        for record in self:
            if record.number_of_hours and record.number_of_hours > 0:
                record.hourly_rate = record.contract_id.wage / record.number_of_hours
            else:
                record.hourly_rate = 0.0
