import secrets
import string
import hashlib
from django.utils import timezone
from accounts.models import User, Token
from obs_flow_common.messages.core import UserDTO


def build_user_dto(user: User) -> UserDTO:
    """
    Converts a User model instance to a UserDTO message struct.
    """
    return UserDTO(
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        is_active=user.is_active,
    )


def generate_secure_token() -> tuple[str, str, str]:
    """
    Generates a secure token, its last 8 characters, and its SHA-256 hash.
    Returns:
        tuple: (raw_token, last_eight, token_hash)
    """
    alphabet = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(64))
    raw_token = f"flow-{random_part}"
    last_eight = raw_token[-8:]
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, last_eight, token_hash


def get_auth_header(request) -> str | None:
    """
    Extracts the Authorization header from the request object.
    Supports both dict-like and object-like request representations.
    """
    if request is None:
        return None
    headers = getattr(request, "headers", None) or request.get("headers", {})
    return headers.get("authorization")


def get_authenticated_user(request) -> User:
    """
    Authenticates a user from the request.
    1. Checks the Authorization header for a Bearer token.
    2. If present, validates the token and returns the associated user.
    3. If not present, checks if request.user is authenticated.
    4. If neither is present, raises a ValueError.
    """
    authorization = get_auth_header(request)
    if authorization:
        if not authorization.startswith("Bearer "):
            raise ValueError("Invalid Authorization header format. Must be 'Bearer <token>'.")

        token_str = authorization[7:].strip()
        token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()

        try:
            token = Token.objects.select_related("user").get(token_hash=token_hash)
            token.last_used_at = timezone.now()
            token.save(update_fields=["last_used_at"])
            return token.user
        except Token.DoesNotExist:
            raise ValueError("Invalid or expired token.")

    if hasattr(request, "user") and request.user and request.user.is_authenticated:
        return request.user

    raise ValueError("Authentication credentials were not provided.")
