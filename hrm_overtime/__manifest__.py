# -*- coding: utf-8 -*-
{
    "name": "hrm_overtime",
    "summary": "Short (1 phrase/line) summary of the module's purpose",
    "description": """
Long description of module's purpose
    """,
    "author": "My Company",
    "website": "https://www.yourcompany.com",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Uncategorized",
    "version": "17.0.1.0",
    # any module necessary for this one to work correctly
    "depends": [
        "hrm_base",
        "hr_attendance",
        "hrm_attendance_integration",
        "hrm_salary",
    ],
    # always loaded
    "data": [
        "security/hr_attendance_overtime_request_security.xml",
        "security/ir.model.access.csv",
        "views/hr_attendance_overtime_request_views.xml",
        "views/hr_attendance_overtime_views.xml",
        "views/hr_overtime_type_views.xml",
    ],
}
