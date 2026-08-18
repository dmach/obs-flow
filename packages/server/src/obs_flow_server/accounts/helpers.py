from accounts.models import User
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
