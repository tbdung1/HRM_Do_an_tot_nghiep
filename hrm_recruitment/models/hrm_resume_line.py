# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmResumeLine(models.Model):
    _name = 'hrm.resume.line'
    _inherit = 'hr.resume.line'
    _description = 'HrmResumeLine'
    employee_id = fields.Many2one('hr.employee', required=False)
    applicant_id = fields.Many2one('hr.applicant', required=False, string="Applicant")

