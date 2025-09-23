# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmEmployeeHealthExamination(models.Model):
    _name = "hrm.employee.health.examination"
    _description = "Employee Health Examination"

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, ondelete="cascade"
    )
    examination_date = fields.Date("Examination Date", required=True)
    hospital = fields.Char("Hospital/Clinic")
    doctor = fields.Char("Doctor")
    diagnosis = fields.Text("Diagnosis")
    treatment = fields.Text("Treatment")
    notes = fields.Text("Notes")
    next_examination_date = fields.Date("Next Examination Date")
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
