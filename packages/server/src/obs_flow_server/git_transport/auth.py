import base64
import hashlib
from django.http import HttpResponse
from accounts.models import User, Token


def authenticate_git_user(request) -> User | None:
    auth_header = request.META.get("HTTP_AUTHORIZATION")
    if not auth_header or not auth_header.startswith("Basic "):
        return None

    try:
        encoded_creds = auth_header.split(" ", 1)[1].strip()
        decoded = base64.b64decode(encoded_creds).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        return None

    # 1. Try by username
    try:
        user = User.objects.get(username__iexact=username)
        if user.is_active:
            # Check user password
            if user.password and user.check_password(password):
                return user

            # Check if password is an API token
            if password:
                tok_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
                if Token.objects.filter(user=user, token_hash=tok_hash).exists():
                    return user
    except User.DoesNotExist:
        pass

    # 2. Check if username itself is an API token
    tok_hash = hashlib.sha256(username.encode("utf-8")).hexdigest()
    try:
        tok = Token.objects.select_related("user").get(token_hash=tok_hash)
        if tok.user.is_active:
            return tok.user
    except Token.DoesNotExist:
        pass

    return None


def unauthorized_response() -> HttpResponse:
    response = HttpResponse("Authentication required\n", status=401, content_type="text/plain")
    response["WWW-Authenticate"] = 'Basic realm="OBS Flow Git"'
    return response
