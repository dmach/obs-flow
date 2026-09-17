from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse


class LoginModalView(LoginView):
    template_name = "accounts/login_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        is_htmx = bool(self.request.headers.get("HX-Request"))
        context["auth_local_enabled"] = settings.AUTH_LOCAL_ENABLED
        context["auth_oidc_enabled"] = settings.AUTH_OIDC_ENABLED
        context["is_htmx"] = is_htmx
        context["extends_template"] = "partials/empty.html" if is_htmx else "base.html"
        return context


class LocalLoginFormView(TemplateView):
    template_name = "accounts/partials/local_login_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AuthenticationForm()
        context["next"] = self.request.GET.get("next", "")
        return context


class CustomLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        if request.headers.get("HX-Request"):
            from django.contrib.auth import logout
            logout(request)
            redirect_url = self.get_success_url()
            response = HttpResponse()
            response["HX-Redirect"] = redirect_url
            return response
        return super().post(request, *args, **kwargs)
