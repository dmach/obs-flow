from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from accounts.models import Token
from accounts.helpers import generate_secure_token


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
        context["is_htmx"] = bool(self.request.headers.get("HX-Request"))
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


@login_required
@require_http_methods(["GET", "POST"])
def token_list(request):
    new_token = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            description = request.POST.get("description", "").strip()
            raw_token, last_eight, token_hash = generate_secure_token()
            Token.objects.create(
                user=request.user,
                last_eight=last_eight,
                token_hash=token_hash,
                description=description or None,
            )
            new_token = raw_token
        elif action == "delete":
            token_id = request.POST.get("token_id")
            if token_id:
                Token.objects.filter(user=request.user, id=token_id).delete()
            return redirect("token_list")

    tokens = Token.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "accounts/tokens.html", {
        "tokens": tokens,
        "new_token": new_token,
    })
