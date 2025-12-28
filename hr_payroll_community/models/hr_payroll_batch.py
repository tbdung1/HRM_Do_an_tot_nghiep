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
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HrPayrollBatch(models.Model):
    """Model để quản lý bảng lương tháng cho tất cả nhân viên"""

    _name = "hr.payroll.batch"
    _description = "Payroll Batch - Bảng Lương Tháng"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_from desc, id desc"

    name = fields.Char(
        string="Tên Bảng Lương",
        required=True,
        tracking=True,
        help="Tên của bảng lương tháng",
    )

    date_from = fields.Date(
        string="Từ Ngày",
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
        tracking=True,
        help="Ngày bắt đầu kỳ lương",
    )

    date_to = fields.Date(
        string="Đến Ngày",
        required=True,
        default=lambda self: (
            date.today().replace(day=1) + relativedelta(months=1, days=-1)
        ),
        tracking=True,
        help="Ngày kết thúc kỳ lương",
    )

    state = fields.Selection(
        [
            ("draft", "Nháp"),
            ("generating", "Đang Tạo"),
            ("generated", "Đã Tạo"),
            ("computed", "Đã Tính"),
            ("done", "Hoàn Thành"),
            ("cancel", "Đã Hủy"),
        ],
        string="Trạng Thái",
        default="draft",
        tracking=True,
        copy=False,
    )

    payslip_ids = fields.One2many(
        "hr.payslip",
        "payroll_batch_id",
        string="Phiếu Lương",
        help="Danh sách phiếu lương của nhân viên trong bảng lương này",
    )

    payslip_run_id = fields.Many2one(
        "hr.payslip.run",
        string="Payslip Run",
        readonly=True,
        help="Liên kết với payslip run (để tương thích với hệ thống cũ)",
    )

    employee_count = fields.Integer(
        string="Số Nhân Viên",
        compute="_compute_statistics",
        store=True,
        help="Tổng số nhân viên trong bảng lương",
    )

    payslip_count = fields.Integer(
        string="Phiếu Lương",
        compute="_compute_statistics",
        store=True,
        help="Tổng số phiếu lương đã tạo",
    )

    total_amount = fields.Float(
        string="Tổng Tiền",
        compute="_compute_statistics",
        store=True,
        help="Tổng tiền lương phải trả",
    )

    send_email = fields.Boolean(
        string="Gửi Email cho Nhân Viên",
        default=False,
        help="Tự động gửi phiếu lương qua email cho nhân viên",
    )

    email_sent_count = fields.Integer(
        string="Email Đã Gửi", readonly=True, help="Số lượng email đã gửi thành công"
    )

    company_id = fields.Many2one(
        "res.company",
        string="Công Ty",
        default=lambda self: self.env.company,
        required=True,
    )

    notes = fields.Text(string="Ghi Chú", help="Ghi chú về bảng lương này")

    create_date = fields.Datetime(string="Ngày Tạo", readonly=True)

    create_uid = fields.Many2one("res.users", string="Người Tạo", readonly=True)

    @api.depends("payslip_ids", "payslip_ids.state", "payslip_ids.total_amount")
    def _compute_statistics(self):
        """Tính toán thống kê"""
        for batch in self:
            batch.payslip_count = len(batch.payslip_ids)
            batch.employee_count = len(batch.payslip_ids.mapped("employee_id"))

            # Chỉ tính tổng tiền của các payslip không bị hủy
            valid_payslips = batch.payslip_ids.filtered(lambda p: p.state != "cancel")
            batch.total_amount = sum(valid_payslips.mapped("total_amount"))

    @api.onchange("date_from", "date_to")
    def _onchange_dates(self):
        """Tự động tạo tên khi thay đổi ngày"""
        if self.date_from and self.date_to:
            self.name = _("Bảng Lương %s/%s") % (
                self.date_from.strftime("%m"),
                self.date_from.strftime("%Y"),
            )

    def _get_eligible_employees(self):
        """
        Lấy danh sách nhân viên có hợp đồng đang chạy trong kỳ
        """
        self.ensure_one()

        # Tìm tất cả hợp đồng active trong kỳ
        contracts = self.env["hr.contract"].search(
            [
                ("state", "=", "open"),
                ("date_start", "<=", self.date_to),
                ("company_id", "=", self.company_id.id),
                "|",
                ("date_end", "=", False),
                ("date_end", ">=", self.date_from),
            ]
        )

        # Lấy danh sách nhân viên từ các hợp đồng
        employees = contracts.mapped("employee_id")

        _logger.info(
            f"Found {len(employees)} employees with active contracts from {self.date_from} to {self.date_to}"
        )

        return employees

    def action_generate_payslips(self):
        """
        Tạo bảng lương cho tất cả nhân viên có hợp đồng đang chạy
        """
        for batch in self:
            if batch.state != "draft":
                raise UserError(_("Chỉ có thể tạo phiếu lương từ trạng thái Nháp!"))

            batch.state = "generating"

            # Lấy danh sách nhân viên đủ điều kiện
            employees = batch._get_eligible_employees()

            if not employees:
                batch.state = "draft"
                raise UserError(
                    _(
                        "Không tìm thấy nhân viên có hợp đồng đang chạy trong kỳ đã chọn!"
                    )
                )

            # Tạo payslip run (để tương thích với hệ thống cũ)
            payslip_run = self.env["hr.payslip.run"].create(
                {
                    "name": batch.name,
                    "date_start": batch.date_from,
                    "date_end": batch.date_to,
                    "state": "draft",
                }
            )
            batch.payslip_run_id = payslip_run.id

            # Tạo bảng lương cho từng nhân viên
            created_count = 0
            skipped_count = 0

            for employee in employees:
                try:
                    # Kiểm tra xem đã có payslip trong kỳ chưa
                    existing_payslip = self.env["hr.payslip"].search(
                        [
                            ("employee_id", "=", employee.id),
                            ("date_from", "=", batch.date_from),
                            ("date_to", "=", batch.date_to),
                            ("state", "!=", "cancel"),
                            ("payroll_batch_id", "=", batch.id),
                        ],
                        limit=1,
                    )

                    if existing_payslip:
                        _logger.info(
                            f"Payslip already exists for {employee.name}, skipping..."
                        )
                        skipped_count += 1
                        continue

                    # Lấy thông tin từ onchange_employee_id
                    slip_data = self.env["hr.payslip"].onchange_employee_id(
                        batch.date_from, batch.date_to, employee.id, contract_id=False
                    )

                    # Chuẩn bị dữ liệu tạo payslip
                    payslip_vals = {
                        "employee_id": employee.id,
                        "name": slip_data["value"].get("name"),
                        "struct_id": slip_data["value"].get("struct_id"),
                        "contract_id": slip_data["value"].get("contract_id"),
                        "date_from": batch.date_from,
                        "date_to": batch.date_to,
                        "company_id": employee.company_id.id,
                        "payslip_run_id": payslip_run.id,
                        "payroll_batch_id": batch.id,
                    }

                    # Thêm input lines và worked days lines
                    if slip_data["value"].get("input_line_ids"):
                        payslip_vals["input_line_ids"] = [
                            (0, 0, x) for x in slip_data["value"].get("input_line_ids")
                        ]

                    if slip_data["value"].get("worked_days_line_ids"):
                        payslip_vals["worked_days_line_ids"] = [
                            (0, 0, x)
                            for x in slip_data["value"].get("worked_days_line_ids")
                        ]

                    # Tạo payslip
                    self.env["hr.payslip"].create(payslip_vals)
                    created_count += 1

                    _logger.info(f"Created payslip for {employee.name}")

                except Exception as e:
                    _logger.error(
                        f"Failed to create payslip for {employee.name}: {str(e)}"
                    )
                    skipped_count += 1
                    continue

            batch.state = "generated"

            # Hiển thị thông báo kết quả
            message = _("Đã tạo thành công!\n\n")
            message += _("Đã tạo: %d phiếu lương\n") % created_count
            if skipped_count > 0:
                message += _("Bỏ qua: %d (đã tồn tại hoặc lỗi)\n") % skipped_count

            batch.message_post(body=message)

        return True

    def action_compute_payslips(self):
        """
        Tính toán tất cả phiếu lương trong bảng lương
        """
        for batch in self:
            if batch.state not in ["generated", "computed"]:
                raise UserError(_("Phải tạo phiếu lương trước khi tính toán!"))

            # Lọc các payslip ở trạng thái draft
            draft_payslips = batch.payslip_ids.filtered(lambda p: p.state == "draft")

            if not draft_payslips:
                raise UserError(_("Không có phiếu lương nào cần tính toán!"))

            # Tính toán payslips
            draft_payslips.action_compute_sheet()

            batch.state = "computed"
            batch.message_post(
                body=_("Đã tính toán %d phiếu lương") % len(draft_payslips)
            )

        return True

    def action_send_emails(self):
        """
        Gửi email phiếu lương cho nhân viên
        """
        for batch in self:
            if batch.state not in ["computed", "done"]:
                raise UserError(_("Phải tính toán phiếu lương trước khi gửi email!"))

            # Lấy các payslip đã verify
            verified_payslips = batch.payslip_ids.filtered(lambda p: p.state == "done")

            if not verified_payslips:
                raise UserError(_("Không có phiếu lương nào đã xác nhận để gửi email!"))

            sent_count, failed_count = batch._send_payslip_emails(verified_payslips)

            batch.email_sent_count = sent_count
            batch.send_email = True

            message = _("Đã gửi email:\n")
            message += _("Thành công: %d\n") % sent_count
            if failed_count > 0:
                message += _("Thất bại: %d\n") % failed_count

            batch.message_post(body=message)

        return True

    def action_mark_done(self):
        """
        Đánh dấu bảng lương là hoàn thành
        """
        for batch in self:
            if batch.state != "computed":
                raise UserError(_("Phải tính toán phiếu lương trước khi hoàn thành!"))

            # Kiểm tra tất cả payslips đã được verify
            unverified = batch.payslip_ids.filtered(
                lambda p: p.state not in ["done", "cancel"]
            )
            if unverified:
                raise UserError(
                    _(
                        "Vẫn còn %d phiếu lương chưa được xác nhận!\n"
                        "Vui lòng xác nhận tất cả phiếu lương trước khi hoàn thành."
                    )
                    % len(unverified)
                )

            batch.state = "done"

            # Đóng payslip run
            if batch.payslip_run_id:
                batch.payslip_run_id.action_close()

            batch.message_post(body=_("Bảng lương đã hoàn thành"))

        return True

    def action_set_to_draft(self):
        """
        Đưa bảng lương về trạng thái nháp
        """
        for batch in self:
            if batch.state == "done":
                raise UserError(_("Không thể đưa bảng lương đã hoàn thành về nháp!"))

            batch.state = "draft"
            batch.message_post(body=_("Đã đưa về trạng thái nháp"))

        return True

    def action_cancel(self):
        """
        Hủy bảng lương
        """
        for batch in self:
            if batch.state == "done":
                raise UserError(_("Không thể hủy bảng lương đã hoàn thành!"))

            batch.state = "cancel"
            batch.message_post(body=_("Đã hủy bảng lương"))

        return True

    def action_view_payslips(self):
        """
        Xem danh sách phiếu lương
        """
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": _("Phiếu Lương"),
            "res_model": "hr.payslip",
            "view_mode": "tree,form",
            "domain": [("payroll_batch_id", "=", self.id)],
            "context": {"default_payroll_batch_id": self.id},
        }

    def _send_payslip_emails(self, payslips):
        """
        Gửi email phiếu lương cho nhân viên

        @param payslips: recordset của hr.payslip
        @return: tuple (sent_count, failed_count)
        """
        sent_count = 0
        failed_count = 0

        # Lấy hoặc tạo email template
        template = self._get_or_create_email_template()

        for payslip in payslips:
            try:
                # Kiểm tra nhân viên có email không
                if not payslip.employee_id.work_email:
                    _logger.warning(
                        f"Employee {payslip.employee_id.name} has no email address"
                    )
                    failed_count += 1
                    continue

                # Gửi email sử dụng template
                template.send_mail(payslip.id, force_send=True, raise_exception=False)
                sent_count += 1
                _logger.info(
                    f"Sent payslip email to {payslip.employee_id.name} ({payslip.employee_id.work_email})"
                )

            except Exception as e:
                _logger.error(
                    f"Failed to send email to {payslip.employee_id.name}: {str(e)}"
                )
                failed_count += 1

        return sent_count, failed_count

    def _get_or_create_email_template(self):
        """
        Lấy hoặc tạo email template cho payslip

        @return: mail.template record
        """
        # Tìm template có external ID
        template = self.env.ref(
            "hr_payroll_community.email_template_payslip", raise_if_not_found=False
        )

        return template

    @api.model
    def create(self, vals):
        """Override create để tự động tạo tên nếu chưa có"""
        if not vals.get("name") and vals.get("date_from"):
            date_from = fields.Date.to_date(vals["date_from"])
            vals["name"] = _("Bảng Lương %s/%s") % (
                date_from.strftime("%m"),
                date_from.strftime("%Y"),
            )
        return super(HrPayrollBatch, self).create(vals)
