# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Hrm_leave(models.Model):
    _name = 'hrm_leave'
    _description = 'Hrm_leave'
    _inherit = 'hr.leave'
