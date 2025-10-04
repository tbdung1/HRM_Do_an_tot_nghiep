from odoo import models, fields, api

class HRMApplicant(models.Model):
    _inherit = 'hr.applicant'
    partner_name = fields.Char(required=True ,string="Applicant's Name")
    resume_line_ids = fields.One2many('hrm.resume.line', 'applicant_id', string="Resume lines")
    def create_employee_from_applicant(self):
        # Gọi super để thực hiện logic mặc định
        action = super().create_employee_from_applicant()
        for applicant in self:
            employee = applicant.emp_id  # employee vừa được tạo
            if employee:
                for line in applicant.resume_line_ids:
                    self.env['hr.resume.line'].create({
                        'employee_id': employee.id,
                        'name': line.name,
                        'date_start': line.date_start,
                        'date_end': line.date_end,
                        'description': line.description,
                        'line_type_id': line.line_type_id.id if line.line_type_id else False,
                    })
        return action

    @api.onchange('job_id')
    def _onchange_job_id_interviewers(self):
        for appicant in self:
            if appicant.job_id:
                appicant.interviewer_ids = appicant.job_id.interviewer_ids
