from odoo import models, fields, api, exceptions
from datetime import datetime, time, timedelta
import ipaddress
import logging
import socket

_logger = logging.getLogger(__name__)

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

    check_in_ip = fields.Char(
        string="Check-in IP Address",
        help="IP address from which the employee checked in."
    )

    @api.constrains('check_in_ip')
    def _check_allowed_ip(self):
        """Kiểm tra IP có được phép check-in hay không"""
        for record in self:
            _logger.info(f"Checking IP: {record.check_in_ip}")
            
            if not record.check_in_ip:
                raise exceptions.ValidationError(
                    'Không thể xác định địa chỉ IP. Vui lòng kiểm tra kết nối mạng!'
                )
            
            allowed_ips = self.env['ir.config_parameter'].sudo().get_param(
                'hrm_attendance.allowed_ips', ''
            )
            _logger.info(f"Allowed IPs: {allowed_ips}")
            _logger.info(f"Client IP: {record.check_in_ip}")
            
            if not allowed_ips:
                continue
            
            allowed_ip_list = [ip.strip() for ip in allowed_ips.split(',')]
            client_ip = record.check_in_ip
            
            is_allowed = False
            for allowed_ip in allowed_ip_list:
                try:
                    # Kiểm tra IP đơn lẻ hoặc dải IP (CIDR)
                    if '/' in allowed_ip:
                        # Dải IP (ví dụ: 192.168.1.0/24)
                        if ipaddress.ip_address(client_ip) in ipaddress.ip_network(allowed_ip, strict=False):
                            is_allowed = True
                            _logger.info(f"IP matched network: {allowed_ip}")
                            break
                    else:
                        # IP đơn lẻ
                        if client_ip == allowed_ip:
                            is_allowed = True
                            _logger.info(f"IP matched: {allowed_ip}")
                            break
                except ValueError as e:
                    _logger.warning(f"Invalid IP format {allowed_ip}: {e}")
                    continue
            
            if not is_allowed:
                raise exceptions.ValidationError(
                    f'Không được phép check-in từ IP {client_ip}. '
                    'Vui lòng kết nối mạng công ty!'
                )

    def _get_local_ip(self):
        """Lấy IP local của máy"""
        try:
            # Tạo socket để lấy IP thực của máy
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            _logger.error(f"Error getting local IP: {e}")
            return None

    @api.model
    def create(self, vals):
        """Lấy IP của client khi tạo bản ghi attendance"""
        _logger.info("=== CREATE ATTENDANCE ===")
        
        client_ip = None
        
        # Thử lấy IP từ request trước
        try:
            import odoo
            if hasattr(odoo, 'http') and hasattr(odoo.http, 'request'):
                request = odoo.http.request
                if request and hasattr(request, 'httprequest'):
                    client_ip = request.httprequest.environ.get('HTTP_X_REAL_IP') or \
                               request.httprequest.environ.get('HTTP_X_FORWARDED_FOR') or \
                               request.httprequest.remote_addr
                    
                    # Nếu là localhost, lấy IP thực của máy
                    if client_ip in ['127.0.0.1', 'localhost', '::1']:
                        client_ip = self._get_local_ip()
                        _logger.info(f"Localhost detected, using local IP: {client_ip}")
                    else:
                        client_ip = client_ip.split(',')[0].strip()
                    
                    _logger.info(f"IP from request: {client_ip}")
        except Exception as e:
            _logger.error(f"Error getting IP from request: {e}")
        
        # Nếu không lấy được từ request, lấy IP local
        if not client_ip:
            client_ip = self._get_local_ip()
            _logger.info(f"Using local IP: {client_ip}")
        
        if client_ip:
            vals['check_in_ip'] = client_ip
            _logger.info(f"Final IP saved: {vals['check_in_ip']}")
        
        return super(HrmAttendance, self).create(vals)

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

        auto_checkout_time = time(17, 0, 0)
        current_time = fields.Datetime.now()
        for record in forgot_checkout_records:
            checkout_datetime = datetime.combine(
                record.check_in.date(),
                auto_checkout_time
            )
            if checkout_datetime <= record.check_in:
                checkout_datetime = record.check_in + timedelta(hours=8)

            record.write({
                'check_out': checkout_datetime,
                'is_auto_checkout': True,
                'auto_checkout_time': current_time,
            })