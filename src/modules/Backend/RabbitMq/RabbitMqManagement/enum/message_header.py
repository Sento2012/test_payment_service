from typing import Final


class MessageHeader:
    ATTEMPT: Final[str] = "x-attempt"  # счётчик попыток обработки (наш, не x-death)
