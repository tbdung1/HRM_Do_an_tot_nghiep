# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmEmployeeEducation(models.Model):
    _name = "hrm.employee.education"
    _description = "Employee Education Background"

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, ondelete="cascade"
    )
    institution = fields.Char("Institution", required=True)
    degree = fields.Char("Degree")
    field_of_study = fields.Char("Field of Study")
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    is_current = fields.Boolean("Current")
    achievement = fields.Text("Achievement")
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
