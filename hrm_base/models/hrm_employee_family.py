# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmEmployeeFamily(models.Model):
    _name = "hrm.employee.family"
    _description = "Employee Family Information"

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, ondelete="cascade"
    )
    name = fields.Char("Name", required=True)
    relationship = fields.Selection(
        [
            ("spouse", "Spouse"),
            ("child", "Child"),
            ("parent", "Parent"),
            ("sibling", "Sibling"),
            ("other", "Other"),
        ],
        string="Relationship",
        required=True,
    )
    date_of_birth = fields.Date("Date of Birth")
    phone = fields.Char("Phone")
    occupation = fields.Char("Occupation")
    is_dependent = fields.Boolean("Is Dependent")
    notes = fields.Text("Notes")
