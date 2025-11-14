# -*- coding: utf-8 -*-
{
    "name": "hrm_contract",
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
    "depends": ["hrm_base", "hr_contract", "hrm_notify"],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/hrm_contract_draft_views.xml",
        "views/hrm_contract_views.xml",
        "views/templates.xml",
        "views/views.xml",
        "report/hrm_contract_templates_draft.xml",
        "report/hrm_contract_reports.xml",
        "report/hrm_contract_templates.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
