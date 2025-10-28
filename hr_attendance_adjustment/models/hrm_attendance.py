from odoo import models, api

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def action_open_adjustment(self):
        """Mở form tạo điều chỉnh chấm công"""
        self.ensure_one()
        return {
            'name': 'Điều chỉnh chấm công',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.adjustment',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_attendance_id': self.id,
                'default_employee_id': self.employee_id.id,
            },
        }
