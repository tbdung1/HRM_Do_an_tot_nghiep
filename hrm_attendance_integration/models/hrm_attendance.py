from odoo import models, fields, api, exceptions
from datetime import datetime, time, timedelta

class HrmAttendance(models.Model):
    _inherit = 'hr.attendance'

    is_auto_checkout = fields.Boolean(
        string="Auto Checkout",
        default=False,
        help="Indicates if the checkout was done automatically by the system."
    )

    auto_checkout_time = fields.Datetime(
        string="Auto Checkout Time",
        help="The time when the automatic checkout was performed."
    )

    def _cron_auto_checkout_forgot_records(self):
        today = fields.Datetime.today()
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)

        forgot_checkout_records = self.search([
            ('check_in', '>=', today_start),
            ('check_in', '<=', today_end),
            ('check_out', '=', False),
            ('is_auto_checkout', '=', False)
        ])

        auto_checkout_time = time(10, 0, 0) #17:00
        current_time = fields.Datetime.now()
        for record in forgot_checkout_records:
            # Tạo thời gian checkout = 17:00 AM cùng ngày với check-in
            checkout_datetime = datetime.combine(
                record.check_in.date(),
                auto_checkout_time
            )
            if checkout_datetime <= record.check_in:
                # Nếu check-in sau 5PM, set checkout = check-in + 8 giờ
                checkout_datetime = record.check_in + timedelta(hours=8)

            record.write({
                'check_out': checkout_datetime,
                'is_auto_checkout': True,
                'auto_checkout_time': current_time,
            })
