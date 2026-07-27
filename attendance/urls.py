from django.urls import path

from .views import (
    api_dashboard_charts,
    api_live_attendance,
    api_session_status,
    dashboard,
    end_session_view,
    index,
    login_view,
    logout_view,
    register_view,
    recognize_view,
    start_session_view,
)
from .views_analytics import analytics_dashboard, notification_mark_read, notifications_list
from .views_confidence import confidence_dashboard
from .views_modules import (
    module_create,
    module_delete,
    module_detail,
    module_edit,
    module_enroll,
    module_list,
    module_unenroll,
)
from .views_performance import (
    assessment_create,
    assessment_detail,
    assessment_list,
    performance_dashboard,
    student_performance,
)
from .views_programmes import (
    programme_create,
    programme_delete,
    programme_detail,
    programme_edit,
    programme_enroll,
    programme_list,
)
from .views_reports import report_print, report_view, reports_hub
from .views_sessions import (
    session_cancel,
    session_create,
    session_detail,
    session_end,
    session_export,
    session_list,
    session_live,
    session_pause,
    session_print,
    session_resume,
    session_start,
)
from .views_students import (
    api_search,
    student_create,
    student_detail,
    student_edit,
    student_export,
    student_list,
    student_upload_images,
)

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("register/", register_view, name="register"),
    path("", index, name="index"),
    path("dashboard/", dashboard, name="dashboard"),
    path("recognize/", recognize_view, name="recognize"),
    path("start-session/", start_session_view, name="start_session"),
    path("end-session/", end_session_view, name="end_session"),
    path("api/session/status/", api_session_status, name="api_session_status"),
    path("api/attendance/live/", api_live_attendance, name="api_live_attendance"),
    path("api/dashboard/charts/", api_dashboard_charts, name="api_dashboard_charts"),
    path("api/search/", api_search, name="api_search"),

    # Students
    path("students/", student_list, name="student_list"),
    path("students/add/", student_create, name="student_create"),
    path("students/export/", student_export, name="student_export"),
    path("students/<int:pk>/", student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", student_edit, name="student_edit"),
    path("students/<int:pk>/upload/", student_upload_images, name="student_upload_images"),
    path("students/<int:pk>/performance/", student_performance, name="student_performance"),

    # Programmes
    path("programmes/", programme_list, name="programme_list"),
    path("programmes/add/", programme_create, name="programme_create"),
    path("programmes/<int:pk>/", programme_detail, name="programme_detail"),
    path("programmes/<int:pk>/edit/", programme_edit, name="programme_edit"),
    path("programmes/<int:pk>/delete/", programme_delete, name="programme_delete"),
    path("programmes/<int:pk>/enroll/", programme_enroll, name="programme_enroll"),

    # Modules (subjects)
    path("modules/", module_list, name="module_list"),
    path("modules/add/", module_create, name="module_create"),
    path("modules/<int:pk>/", module_detail, name="module_detail"),
    path("modules/<int:pk>/edit/", module_edit, name="module_edit"),
    path("modules/<int:pk>/delete/", module_delete, name="module_delete"),
    path("modules/<int:pk>/enroll/", module_enroll, name="module_enroll"),
    path("modules/<int:pk>/unenroll/<int:student_id>/", module_unenroll, name="module_unenroll"),

    # Backwards-compatible course URLs → modules
    path("courses/", module_list, name="course_list"),
    path("courses/add/", module_create, name="course_create"),
    path("courses/<int:pk>/", module_detail, name="course_detail"),
    path("courses/<int:pk>/edit/", module_edit, name="course_edit"),
    path("courses/<int:pk>/delete/", module_delete, name="course_delete"),
    path("courses/<int:pk>/enroll/", module_enroll, name="course_enroll"),
    path("courses/<int:pk>/unenroll/<int:student_id>/", module_unenroll, name="course_unenroll"),

    # Sessions
    path("sessions/", session_list, name="session_list"),
    path("sessions/add/", session_create, name="session_create"),
    path("sessions/<int:pk>/", session_detail, name="session_detail"),
    path("sessions/<int:pk>/live/", session_live, name="session_live"),
    path("sessions/<int:pk>/start/", session_start, name="session_start_action"),
    path("sessions/<int:pk>/pause/", session_pause, name="session_pause"),
    path("sessions/<int:pk>/resume/", session_resume, name="session_resume"),
    path("sessions/<int:pk>/end/", session_end, name="session_end_action"),
    path("sessions/<int:pk>/cancel/", session_cancel, name="session_cancel"),
    path("sessions/<int:pk>/export/", session_export, name="session_export"),
    path("sessions/<int:pk>/print/", session_print, name="session_print"),

    # Performance
    path("performance/", performance_dashboard, name="performance_dashboard"),
    path("performance/assessments/", assessment_list, name="assessment_list"),
    path("performance/assessments/add/", assessment_create, name="assessment_create"),
    path("performance/assessments/<int:pk>/", assessment_detail, name="assessment_detail"),

    # Confidence
    path("confidence/", confidence_dashboard, name="confidence_dashboard"),

    # Reports
    path("reports/", reports_hub, name="reports_hub"),
    path("reports/<str:report_type>/", report_view, name="report_view"),
    path("reports/<str:report_type>/print/", report_print, name="report_print"),

    # Analytics & notifications
    path("analytics/", analytics_dashboard, name="analytics_dashboard"),
    path("notifications/", notifications_list, name="notifications_list"),
    path("notifications/<int:pk>/read/", notification_mark_read, name="notification_mark_read"),
]
