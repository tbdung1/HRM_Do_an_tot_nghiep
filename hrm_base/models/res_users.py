# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    tax_identification_number = fields.Char(
        related="employee_id.tax_identification_number",
        readonly=False,
        related_sudo=False,
    )

    health_status = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("fair", "Fair"),
            ("poor", "Poor"),
        ],
        related="employee_id.health_status",
        readonly=False,
        related_sudo=False,
    )
    is_hr = fields.Boolean(
        related="employee_id.is_hr",
        readonly=True,
        store=False,
    )
    id_number = fields.Char(
        related="employee_id.id_number",
        readonly=False,
        related_sudo=False,
    )

    health_insurance_number = fields.Char(
        related="employee_id.health_insurance_number",
        readonly=False,
        related_sudo=False,
    )

    education_level = fields.Selection(
        [
            ("high_school", "High School"),
            ("college", "College"),
            ("bachelor", "Bachelor"),
        ],
        related="employee_id.education_level",
        readonly=False,
        related_sudo=False,
    )

    @property
    def SELF_READABLE_FIELDS(self):
        """Extend readable fields with custom fields"""
        # Lấy danh sách field gốc từ parent
        base_fields = super().SELF_READABLE_FIELDS

        # Thêm custom fields
        custom_fields = [
            "health_status",
            "is_hr",
            "id_number",
            "tax_identification_number",
            "health_insurance_number",
            "education_level",
        ]

        # Combine lists và loại bỏ duplicate
        return list(set(base_fields + custom_fields))

    @property
    def SELF_WRITEABLE_FIELDS(self):
        """Extend writable fields with custom fields"""
        # Lấy danh sách field gốc từ parent
        base_fields = super().SELF_WRITEABLE_FIELDS

        # Thêm custom writable fields (loại bỏ is_hr vì readonly=True)
        custom_writable_fields = [
            "health_status",
            "id_number",
            "tax_identification_number",
            "health_insurance_number",
            "education_level",
        ]

        # Combine lists và loại bỏ duplicate
        return list(set(base_fields + custom_writable_fields))
