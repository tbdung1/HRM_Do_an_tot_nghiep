# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta

_logger = logging.getLogger(__name__)


class HrmContract(models.Model):
    _inherit = "hr.contract"

    allowance = fields.Monetary(
        "Allowance",
        tracking=True,
        help="Employee's monthly allowance.",
        group_operator="avg",
    )

    def _gender_label(self):
        self.ensure_one()
        mapping = {
            "male": _("Male"),
            "female": _("Female"),
            "other": _("Other"),
        }
        return mapping.get(self.employee_id.gender)

    def _get_bot_hrm(self):
        bot_user = (
            self.env["res.users"].sudo().search([("login", "=", "bot_hrm")], limit=1)
        )
        if not bot_user:
            bot_user = (
                self.env["res.users"]
                .sudo()
                .create(
                    {
                        "name": "HRM Bot",
                        "login": "bot_hrm",
                        "email": "bot_hrm@example.com",
                    }
                )
            )
        return bot_user

    def action_view_attachments(self):
        """View attachments"""
        return {
            "name": _("Supporting Documents"),
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "view_mode": "kanban,tree,form",
            "domain": [("res_model", "=", self._name), ("res_id", "=", self.id)],
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
            },
        }

    def _create_channel(self, partner_id, bot_user, chat_message):
        try:
            chan_info = (
                self.env["discuss.channel"]
                .with_user(bot_user)
                .channel_get([partner_id])
            )
            channel = self.env["discuss.channel"].browse(chan_info["id"])

            # Gửi tin nhắn vào đúng channel này
            channel.with_context(mail_create_nosubscribe=True).message_post(
                body=chat_message,
                author_id=bot_user.id,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
        except Exception as e:
            _logger.error(f"Error creating channel or sending message: {e}")

    def _sent_notify(self, emp_contract):
        try:
            days_remaining = (emp_contract.date_end - fields.Date.today()).days
            chat_message = _(
                'Contract "{contract_name}" for employee "{employee_name}" will expire in {days} days.'
            ).format(
                contract_name=emp_contract.name,
                employee_name=emp_contract.employee_id.name,
                days=days_remaining,
            )
            bot_user = self._get_bot_hrm()
            hr = emp_contract.employee_id.parent_id.user_id.partner_id

            job_ceo = self.env.ref("hr.job_ceo")
            employees = self.env["hr.employee"].search([("job_id", "=", job_ceo.id)])
            partners = employees.mapped("user_id.partner_id")
            partners |= hr
            partners |= emp_contract.employee_id.user_id.partner_id
            for partner in partners:
                self._create_channel(partner.id, bot_user, chat_message)
                mail = self.env["mail.mail"].create(
                    {
                        "subject": _("Contract Expiration Notice"),
                        "body_html": _(
                            """<p>Dear {partner_name},</p>
                        <p>{message}</p>
                        <p>Best regards.</p>"""
                        ).format(partner_name=partner.name, message=chat_message),
                        "email_to": partner.email,
                        "email_from": "n21dccn112@student.ptithcm.edu.vn",
                    }
                )
                mail.send()
        except Exception as e:
            _logger.error(f"Error sending contract expiration notification: {e}")

    @api.model
    def _sent_expired_contract(self):
        deadline = fields.Date.today() + timedelta(days=30)
        contracts = self.search(
            [
                ("date_end", "!=", False),
                ("date_end", ">=", fields.Date.today()),
                ("date_end", "<=", deadline),
                ("state", "=", "open"),
            ]
        )
        for contract in contracts:
            contract.sudo()._sent_notify(contract)

    def action_active_contract(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only contracts in draft state can be activated."))
            rec.sudo().write({"state": "open"})

    def action_cancel_contract(self):
        for rec in self:
            if rec.state == "open": 
                if not rec.notes:
                    raise UserError(
                        _(
                            "Cannot cancel contract %s without notes." %
                            rec.name,
                        )
                    )
            rec.sudo().write({"state": "cancel"})
    
    def action_set_to_draft(self):
        for rec in self:
            rec.sudo().write({"state": "draft"})