# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmEmployeeDocument(models.Model):
    _name = "hrm.employee.document"
    _description = "Employee Documents"

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, ondelete="cascade"
    )
    name = fields.Char("Document Name", required=True)
    document_type = fields.Selection(
        [
            ("contract", "Labor Contract"),
            ("contract_appendix", "Contract Appendix"),
            ("salary_adjustment", "Salary Adjustment"),
            ("certificate", "Certificate"),
            ("diploma", "Diploma"),
            ("identification", "Identification"),
            ("other", "Other"),
        ],
        string="Document Type",
        required=True,
    )
    issue_date = fields.Date("Issue Date")
    expiry_date = fields.Date("Expiry Date")
    document_file = fields.Binary("Document File")
    notes = fields.Text("Notes")
