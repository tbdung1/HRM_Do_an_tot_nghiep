{
    'name': 'HRM Recruitment',
    'version': '1.0',
    'summary': 'Quản lý tuyển dụng nhân sự (giống hr.applicant)',
    'description': 'Module quản lý ứng viên, quy trình tuyển dụng',
    'category': 'Human Resources',
    'author': 'Bạn',
    'depends': ['hr', 'hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'views/hrm_applicant_views.xml',
        'views/hrm_menu_views.xml',
    ],
    'application': True,
}
