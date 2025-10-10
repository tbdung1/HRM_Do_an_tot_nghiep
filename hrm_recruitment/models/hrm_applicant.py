from odoo import models, fields, api, exceptions

class HRMApplicant(models.Model):
    _inherit = 'hr.applicant'
    partner_name = fields.Char(required=True ,string="Applicant's Name")
    resume_line_ids = fields.One2many('hrm.resume.line', 'applicant_id', string="Resume lines")
    is_last_stage = fields.Boolean(
        string="Is Last Stage",
        compute="_compute_is_last_stage",
        store=False
    )
    stage_id = fields.Many2one(
        'hr.recruitment.stage',
        string='Stage',
        default=lambda self: self._default_stage_id()
    )
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

    def next_stage(self):
        for rec in self:
            if not rec.stage_id:
                raise exceptions.UserError(("Ứng viên %s chưa có stage hiện tại.") % rec.display_name)

            current_seq = rec.stage_id.sequence or 0
            job = rec.job_id

            # Domain stage theo job
            if job:
                domain = [
                    '|',
                    ('job_ids', '=', job.id),
                    ('job_ids', '=', False)
                ]
            else:
                domain = [('job_ids', '=', False)]

            # Lấy tất cả stage áp dụng theo thứ tự sequence
            stages = self.env['hr.recruitment.stage'].search(domain, order='sequence asc, id asc')

            # Tìm stage tiếp theo trong danh sách
            next_stage = False
            found = False
            for stage in stages:
                if found:
                    next_stage = stage
                    break
                if stage.id == rec.stage_id.id:
                    found = True

            if not next_stage:
                raise exceptions.UserError(("Không còn stage nào sau stage hiện tại cho ứng viên %s.") % rec.display_name)

            rec.stage_id = next_stage.id

    @api.model
    def _default_stage_id(self):
        """Tìm stage có sequence nhỏ nhất (thường là 0) của job hiện tại hoặc global."""
        stage = self.env['hr.recruitment.stage'].search([], order='sequence asc', limit=1)
        return stage.id if stage else False

    def _compute_is_last_stage(self):
        for rec in self:
            rec.is_last_stage = False
            if not rec.stage_id:
                continue

            # Domain stage theo job (job riêng hoặc global)
            domain = [
                '|',
                ('job_ids', '=', rec.job_id.id),
                ('job_ids', '=', False)
            ]
            stages = self.env['hr.recruitment.stage'].search(domain, order="sequence desc, id desc", limit=1)

            # Nếu stage hiện tại là stage cuối
            if stages and stages.id == rec.stage_id.id:
                rec.is_last_stage = True