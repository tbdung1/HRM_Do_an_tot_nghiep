# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from collections import defaultdict
from datetime import timedelta

from pytz import utc

from odoo import models
from odoo.tools import float_utils
import logging

# This will generate 16th of days
ROUNDING_FACTOR = 16


class ResourceMixin(models.AbstractModel):
    """Inherit resource_mixin for getting Worked Days"""
    _inherit = "resource.mixin"

    def get_work_days_data(self, from_datetime, to_datetime,
                           compute_leaves=True, calendar=None, domain=None):
        """
        Tính số ngày làm việc theo 2 cách:
        1. days: Theo lịch làm việc (calendar) - như cũ
        2. work_days: Theo attendance thực tế (số ngày có chấm công)
        
        Returns a dict {'days': n, 'hours': h, 'work_days': w} containing:
        - days: số ngày theo calendar
        - hours: tổng số giờ
        - work_days: số ngày thực tế có chấm công
        """
        resource = self.resource_id
        calendar = calendar or self.resource_calendar_id
        # naive datetimes are made explicit in UTC
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=utc)
        
        # ===== TÍNH THEO CALENDAR (GIỮ NGUYÊN NHƯ CŨ) =====
        # total hours per day: retrieve attendances with one extra day margin,
        # in order to compute the total hours on the first and last days
        from_full = from_datetime - timedelta(days=1)
        to_full = to_datetime + timedelta(days=1)
        intervals = calendar._attendance_intervals_batch(from_full, to_full,
                                                         resource)
        day_total = defaultdict(float)
        for start, stop, meta in intervals[resource.id]:
            day_total[start.date()] += (stop - start).total_seconds() / 3600
        # actual hours per day
        if compute_leaves:
            intervals = calendar._work_intervals_batch(from_datetime,
                                                       to_datetime, resource,
                                                       domain)
        else:
            intervals = calendar._attendance_intervals_batch(from_datetime,
                                                             to_datetime,
                                                             resource)
        day_hours = defaultdict(float)
        for start, stop, meta in intervals[resource.id]:
            day_hours[start.date()] += (stop - start).total_seconds() / 3600
        # compute number of days as quarters (theo calendar)
        days_by_calendar = sum(
            float_utils.round(ROUNDING_FACTOR * day_hours[day] / day_total[
                day]) / ROUNDING_FACTOR
            for day in day_hours
        )
        total_hours = sum(day_hours.values())
        
        # ===== TÍNH THEO ATTENDANCE THỰC TẾ (MỚI) =====
        # Lấy tất cả bản ghi chấm công trong khoảng thời gian
        attendance_records = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
            ('check_in', '>=', from_datetime),
            ('check_in', '<=', to_datetime),
            ('check_out', '!=', False),  # Chỉ lấy những bản ghi đã checkout
        ])

        bonus_records = self.env['hr.payroll.adjustment'].search([
            ('employee_id', '=', self.id),
            ('state', '=', 'approved'),
            ('adjustment_type', '=', 'bonus'),
            ('approved_date', '>=', from_datetime),
            ('approved_date', '<=', to_datetime),
        ])
        logging.info("Bonus Records: %s", bonus_records)
        
        # Tính số ngày dựa trên số giờ làm việc của từng ngày
        daily_hours = defaultdict(float)
        for attendance in attendance_records:
            check_in_date = attendance.check_in.date()
            # Cộng dồn số giờ làm việc của mỗi ngày
            daily_hours[check_in_date] += attendance.worked_hours
        
        # Tính số ngày dựa trên quy tắc:
        # - Nếu > 2 giờ và < 5 giờ: tính 0.5 ngày
        # - Nếu >= 5 giờ: tính 1 ngày
        # - Nếu <= 2 giờ: tính 0 ngày
        work_days_actual = 0.0
        for date, hours in daily_hours.items():
            if hours > 2 and hours < 5:
                work_days_actual += 0.5
            elif hours >= 5:
                work_days_actual += 1.0
            # Nếu hours <= 2, không cộng gì (tức là 0 ngày)
        
        return {
            'days': days_by_calendar,        # Số ngày theo calendar (như cũ)
            'hours': total_hours,             # Tổng giờ
            'work_days': work_days_actual,    # Số ngày theo quy tắc mới
        }
