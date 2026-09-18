from django.urls import path
from .views import LoginModalView, LocalLoginFormView, CustomLogoutView, token_list, preferences

urlpatterns = [
    path("login/", LoginModalView.as_view(), name="login"),
    path("login/local/", LocalLoginFormView.as_view(), name="local_login_form"),
    path("logout/", CustomLogoutView.as_view(next_page="home"), name="logout"),
    path("tokens/", token_list, name="token_list"),
    path("preferences/", preferences, name="preferences"),
]
