# -*- coding: utf-8 -*-
{
    "name": "HRM Base",
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
    "depends": ["hr", "mail", "contacts"],
    # always loaded
    "data": [
        "security/hr.security.xml",
        "security/ir.model.access.csv",
        "views/hrm_employee_public_views.xml",
        "views/hrm_employees_views.xml",
        "views/hrm_menu_views.xml",
        "views/res_users_views.xml",
        # "#views/hrm_employee_health_examination_views.xml",
    ],
    "application": True,  # <<< HIỂN THỊ NHƯ APP
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
    "external_dependencies": {
        "python": ["requests"],
    },
}
