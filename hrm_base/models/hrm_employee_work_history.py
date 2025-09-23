# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmEmployeeWorkHistory(models.Model):
    _name = "hrm.employee.work.history"
    _description = "Employee Work History"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, ondelete="cascade")
    company = fields.Char("Company", required=True)
    position = fields.Char("Position", required=True)
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    is_current = fields.Boolean("Current")
    responsibilities = fields.Text("Responsibilities")
    achievements = fields.Text("Achievements")
    reference_name = fields.Char("Reference Name")
    reference_contact = fields.Char("Reference Contact")


