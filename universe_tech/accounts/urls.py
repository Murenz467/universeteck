from django.contrib.auth import views as auth
from django.urls import path, reverse_lazy
from core.ratelimit import lockout_login, ratelimit
from . import views, two_factor

urlpatterns = [
    path("register/", ratelimit("register", 10, 3600)(views.register), name="register"),
    path("login/", lockout_login(auth.LoginView.as_view()), name="login"),
    path("2fa/", two_factor.two_factor, name="two_factor"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("password-reset/", ratelimit("pwreset", 5, 3600)(auth.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html",
        email_template_name="registration/password_reset_email.txt",
        subject_template_name="registration/password_reset_subject.txt",
        success_url=reverse_lazy("password_reset_done"))), name="password_reset"),
    path("password-reset/sent/", auth.PasswordResetDoneView.as_view(
        template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", ratelimit("pwconfirm", 20, 3600)(auth.PasswordResetConfirmView.as_view(
        template_name="registration/password_reset_confirm.html",
        success_url=reverse_lazy("password_reset_complete"))), name="password_reset_confirm"),
    path("reset/done/", auth.PasswordResetCompleteView.as_view(
        template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
    path("password-change/", auth.PasswordChangeView.as_view(
        template_name="registration/password_change.html", success_url=reverse_lazy("profile")), name="password_change"),
    path("", views.dashboard, name="dashboard"),
]
