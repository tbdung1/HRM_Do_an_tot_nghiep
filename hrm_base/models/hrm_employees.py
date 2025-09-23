# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmEmployees(models.Model):
    _inherit = "hr.employee"

    # Personal Information - Civil Status (adding to existing fields)
    id_number = fields.Char("ID Number")  



    tax_identification_number = fields.Char("Tax Identification Number")
    health_insurance_number = fields.Char("Health Insurance Number")

    # Additional personal information
    ethnicity = fields.Char("Ethnicity")
    religion = fields.Char("Religion")

    # Education (extending Odoo's certificate field)
    education_level = fields.Selection(
        [
            ("high_school", "High School"),
            ("college", "College"),
            ("bachelor", "Bachelor"),
            ("master", "Master"),
            ("phd", "PhD"),
            ("other", "Other"),
        ],
        string="Education Level",
    )  # Already exists in your model

    # Work history and detailed education background
    education_background_ids = fields.One2many(
        "hrm.employee.education", "employee_id", string="Education Background"
    )
    work_history_ids = fields.One2many(
        "hrm.employee.work.history", "employee_id", string="Work History"
    )

    # Family Information (extending Odoo's spouse info)
    family_member_ids = fields.One2many(
        "hrm.employee.family", "employee_id", string="Family Members"
    )

    # Health Information
    health_status = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("fair", "Fair"),
            ("poor", "Poor"),
        ],
        string="Health Status",
    )
    medical_history = fields.Text("Medical History")
    health_examination_ids = fields.One2many(
        "hrm.employee.health.examination", "employee_id", string="Health Examinations"
    )

    # Job Information (extending Odoo's job_id, department_id, etc.)
    job_level = fields.Selection(
        [
            ("staff", "Staff"),
            ("senior", "Senior"),
            ("lead", "Lead"),
            ("manager", "Manager"),
            ("director", "Director"),
            ("executive", "Executive"),
        ],
        string="Job Level",
    )
    # employee_group_id = fields.Many2one("hrm.employee.group", string="Employee Group")

    # Document Attachments (beyond what Odoo already has)
    document_ids = fields.One2many(
        "hrm.employee.document", "employee_id", string="Documents"
    )
