from django.urls import path

from .views import (
    dashboard,
    end_session_view,
    index,
    login_view,
    logout_view,
    register_view,
    recognize_view,
    start_session_view,
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
]
