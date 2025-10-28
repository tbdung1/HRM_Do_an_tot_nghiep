{
    'name': 'HRM Attendance Adjustment',
    'version': '17.0',
    'summary': 'Quản lý chấm công',
    'description': 'Yêu cầu điều chỉnh chấm công cho nhân viên',
    'category': 'Human Resources',
    'author': 'Phuc Le',
    'depends': ['hr', 'hrm_base', 'hr_attendance'],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_attendance_adjustment_views.xml",
        "views/hr_attendance_inherit.xml"
        ],
    'application': True,
    'installable': True,
}
