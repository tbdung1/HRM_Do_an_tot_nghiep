# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrmEmployees(models.Model):
    _inherit = "hr.employee"

    is_hr = fields.Boolean(compute="_compute_is_hr", store=False)

    def _compute_is_hr(self):
        user = self.env.user
        for rec in self:
            rec.is_hr = user.has_group("hr.group_hr_user") or user.has_group(
                "hr.group_hr_manager"
            )

    current_leave_id = fields.Many2one(
        groups="hr_holidays.group_hr_holidays_user,hr.group_hr_user,base.group_user"
    )

    # Personal Information - Civil Status (adding to existing fields)
    id_number = fields.Char("ID Number")  

    tax_identification_number = fields.Char(string="Tax Identification Number", groups="hr.group_hr_user")
    health_insurance_number = fields.Char(string="Health Insurance Number", groups="hr.group_hr_user")

    # Education (extending Odoo's certificate field)
    education_level = fields.Selection(
        [
            ("high_school", "High School"),
            ("college", "College"),
            ("bachelor", "Bachelor"),
        ],
        string="Education Level",
        groups="hr.group_hr_user",
    ) 

    # Health Information
    health_status = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("fair", "Fair"),
            ("poor", "Poor"),
        ],
        string="Health Status",
        groups="hr.group_hr_user",
    )


    def get_formview_id(self, access_uid=None):
        """
        Override để tự động redirect view dựa trên user groups
        """

        _logger.info("=== GET_FORMVIEW_ID CALLED ===")
        _logger.info(f"access_uid: {access_uid}")
        _logger.info(f"current user: {self.env.user.name}")

        if access_uid:
            self_sudo = self.with_user(access_uid)
        else:
            self_sudo = self

        _logger.info(f"has hr.group_hr_user: {self_sudo.user_has_groups('hr.group_hr_user')}")

        # HR Users → Dùng view gốc (full access)
        if self_sudo.user_has_groups('hr.group_hr_user'):
            return super().get_formview_id(access_uid=access_uid)

        # Non-HR Users → Extended public view
        return self.env.ref('hrm_base.hr_employee_extended_public_view_form').id

    def get_formview_action(self, access_uid=None):
        """
        Override để redirect model cho non-HR users
        """
        res = super().get_formview_action(access_uid=access_uid)
        _logger.info(f"Original action: {res}")

        if access_uid:
            self_sudo = self.with_user(access_uid)
        else:
            self_sudo = self

        # Non-HR Users → Redirect sang hr.employee.public
        if not self_sudo.user_has_groups('hr.group_hr_user'):
            res['res_model'] = 'hr.employee.public'
            _logger.info(f"Redirected to public model: {res}")

        return res
