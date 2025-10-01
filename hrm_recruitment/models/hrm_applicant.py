from odoo import models, fields, api

class HRMApplicant(models.Model):
    _inherit = 'hr.applicant'
    partner_name = fields.Char(required=True ,string="Applicant's Name")
    resume_line_ids = fields.One2many('hrm.resume.line', 'applicant_id', string="Resume lines")
