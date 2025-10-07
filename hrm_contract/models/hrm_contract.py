# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
_logger = logging.getLogger(__name__)


class HrmContract(models.Model):
    _inherit = "hr.contract"
    
    def _get_bot_hrm(self):
        bot_user = self.env['res.users'].sudo().search([('login', '=', 'bot_hrm')], limit=1)
        if not bot_user:
            bot_user = self.env['res.users'].sudo().create({
                'name': 'HRM Bot',
                'login': 'bot_hrm',
                'email': 'bot_hrm@example.com'
            })
        return bot_user

    def _create_channel(self, partner_id, bot_user, chat_message):
        try:
            chan_info = self.env['discuss.channel'].with_user(bot_user).channel_get([partner_id])
            channel = self.env['discuss.channel'].browse(chan_info['id'])

            # Gửi tin nhắn vào đúng channel này
            channel.with_context(mail_create_nosubscribe=True).message_post(
                body=chat_message,
                author_id=bot_user.id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
        except Exception as e:
            _logger.error(f"Error creating channel or sending message: {e}")
    
    def _sent_notify(self, emp_contract):
        try:
            chat_message = f"Hợp đồng của nhân viên \"{emp_contract.employee_id.name}\" còn {(emp_contract.date_end - fields.Date.today()).days} ngày nữa sẽ hết hạn."
            bot_user = self._get_bot_hrm()
            hr = emp_contract.employee_id.parent_id.user_id.partner_id
            
            job_ceo = self.env.ref('hr.job_ceo')
            employees = self.env['hr.employee'].search([('job_id', '=', job_ceo.id)])
            partners = employees.mapped('user_id.partner_id')
            partners |= hr
            partners |= emp_contract.employee_id.user_id.partner_id
            for partner in partners:
                self._create_channel(partner.id, bot_user, chat_message)
        except Exception as e:
            _logger.error(f"Error sending contract expiration notification: {e}")

    @api.model
    def _sent_expired_contract(self):
        deadline = fields.Date.today() + timedelta(days=30)
        contracts = self.search([('date_end', '!=', False),
                                 ('date_end', '>=', fields.Date.today()),
                                 ('date_end', '<=', deadline),
                                 ('state', '=', 'open')])
        for contract in contracts:
            contract.sudo()._sent_notify(contract)
