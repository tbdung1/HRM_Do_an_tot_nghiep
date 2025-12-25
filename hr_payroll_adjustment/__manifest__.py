# -*- coding: utf-8 -*-
{
    'name': 'HR Payroll Adjustment',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Quản lý trợ cấp và khấu trừ lương nhân viên',
    'description': """
        Module quản lý trợ cấp và khấu trừ lương
        ==========================================
        
        Tính năng:
        - Nhân viên có thể gửi yêu cầu trợ cấp hoặc khấu trừ
        - HR có thể duyệt hoặc từ chối yêu cầu
        - Tích hợp với hệ thống tính lương
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['hr', 'hr_payroll_community'],
    'data': [
        'security/security.xml',
        'views/hr_payroll_adjustment_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
