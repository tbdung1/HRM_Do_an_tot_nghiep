{
    'name': 'HRM Attendance Supplement',
    'version': '17.0',
    'summary': 'Quản lý bổ sung chấm công',
    'description': 'Yêu cầu bổ sung chấm công cho nhân viên',
    'category': 'Human Resources',
    'author': 'Phuc Le',
    'depends': ['hr', 'hrm_base', 'hr_attendance'],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_attendance_supplement_views.xml",
        "security/hr_attendance_supplement_rules.xml"
        ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
