{
    'name': 'HRM Attendance',
    'version': '17.0',
    'summary': 'Quản lý chấm công',
    'description': 'Module quản lý ứng viên, quy trình tuyển dụng',
    'category': 'Human Resources',
    'author': 'Phuc Le',
    'depends': ['hr', 'hrm_base', 'hr_attendance'],
    "data": [
        "security/ir.model.access.csv",
        # "views/hrm_attendance_views.xml",
        "views/hrm_attendance_menu_vỉews.xml",
        "security/hr_attendance_security.xml.xml"
        ],
    'application': True,
}
