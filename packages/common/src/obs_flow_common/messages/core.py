import msgspec


class UserDTO(msgspec.Struct):
    """
    DTO (Data Transfer Object) representing a serialized user.
    """
    username: str
    full_name: str | None
    email: str | None
    is_active: bool
