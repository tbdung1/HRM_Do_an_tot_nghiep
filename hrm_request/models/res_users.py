# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Res_users(models.Model):
    _inherit = "res.users"

    def action_create_update_request(self):
        self.ensure_one()
        return {
            "name": _("Create Update Request"),
            "type": "ir.actions.act_window",
            "res_model": "hrm.employee.update.request",
            "view_mode": "form",
            "context": {"default_employee_id": self.id},
            "target": "new",
        }
