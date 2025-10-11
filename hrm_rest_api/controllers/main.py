from odoo import http
from odoo.http import request
import json

class LoginAPI(http.Controller):

    @http.route('/api/login', type='http', auth='public', methods=['POST'], csrf=False)
    def login(self, **kw):
        # Lấy JSON body
        try:
            data = json.loads(request.httprequest.get_data(as_text=True))
        except Exception:
            return request.make_response(
                json.dumps({"success": False, "error": "Invalid JSON"}),
                headers=[('Content-Type', 'application/json')]
            )

        login = data.get('login')
        password = data.get('password')

        if not login or not password:
            return request.make_response(
                json.dumps({"success": False, "error": "Missing login or password"}),
                headers=[('Content-Type', 'application/json')]
            )

        # Lấy tên DB hiện tại
        db = request.env.cr.dbname

        try:
            # Sử dụng session.authenticate thay cho res.users._authenticate
            uid = request.session.authenticate(db, login, password)
        except Exception:
            uid = False

        if uid:
            user = request.env['res.users'].sudo().browse(uid)
            return request.make_response(
                json.dumps({
                    "success": True,
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "login": user.login
                    }
                }),
                headers=[('Content-Type', 'application/json')]
            )
        else:
            return request.make_response(
                json.dumps({"success": False, "error": "Invalid login or password"}),
                headers=[('Content-Type', 'application/json')]
            )
