{
    'name': 'HRM Recruitment',
    'version': '17.0',
    'summary': 'Quản lý tuyển dụng nhân sự (giống hr.applicant)',
    'description': 'Module quản lý ứng viên, quy trình tuyển dụng',
    'category': 'Human Resources',
    'author': 'Bạn',
    'depends': ['hr', 'hr_recruitment', 'hrm_base', 'hr_skills', 'hr_recruitment_skills'],
    "data": [
        "security/ir.model.access.csv",
        "views/hrm_applicant_views.xml",
        "views/hrm_job_views.xml",
        "views/hrm_menu_views.xml", 
        "views/hrm_resume_line_views.xml"
        ],
    
    'application': True,
}
