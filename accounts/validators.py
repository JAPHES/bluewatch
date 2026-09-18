from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible


@deconstructible
class BlueWatchUsernameValidator(RegexValidator):
    regex = r"^[\w.@+\-](?:[\w.@+\- ]{0,148}[\w.@+\-])?\Z"
    message = (
        "Enter a valid username. It may contain letters, numbers, spaces, "
        "and the characters @ . + - _. It cannot start or end with a space."
    )
    flags = 0


def normalize_username_spaces(value):
    """Trim a username and collapse repeated whitespace to one space."""
    return " ".join(str(value).split())
