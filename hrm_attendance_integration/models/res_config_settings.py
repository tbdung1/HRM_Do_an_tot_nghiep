from odoo import fields, models, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_time_restriction = fields.Boolean(
        string="Enable Time Restriction",
        config_parameter='hrm_attendance.enable_time_restriction',
        help="Enable or disable check-in/check-out time restrictions"
    )
    
    check_in_start_time = fields.Char(
        string="Check-in Start Time",
        config_parameter='hrm_attendance.check_in_start_time',
        default='07:00',
        help="Format: HH:MM (e.g., 07:00)"
    )
    
    check_in_end_time = fields.Char(
        string="Check-in End Time",
        config_parameter='hrm_attendance.check_in_end_time',
        default='09:00',
        help="Format: HH:MM (e.g., 09:00)"
    )
    
    check_out_start_time = fields.Char(
        string="Check-out Start Time",
        config_parameter='hrm_attendance.check_out_start_time',
        default='16:00',
        help="Format: HH:MM (e.g., 16:00)"
    )
    
    check_out_end_time = fields.Char(
        string="Check-out End Time",
        config_parameter='hrm_attendance.check_out_end_time',
        default='19:00',
        help="Format: HH:MM (e.g., 19:00)"
    )

    @api.constrains('check_in_start_time', 'check_in_end_time', 
                    'check_out_start_time', 'check_out_end_time')
    def _check_time_format(self):
        """Validate time format HH:MM"""
        from datetime import datetime
        
        for record in self:
            time_fields = [
                ('check_in_start_time', record.check_in_start_time),
                ('check_in_end_time', record.check_in_end_time),
                ('check_out_start_time', record.check_out_start_time),
                ('check_out_end_time', record.check_out_end_time),
            ]
            
            for field_name, field_value in time_fields:
                if field_value:
                    try:
                        datetime.strptime(field_value, '%H:%M')
                    except ValueError:
                        raise models.ValidationError(
                            f'{field_name} must be in format HH:MM (e.g., 07:00)'
                        )