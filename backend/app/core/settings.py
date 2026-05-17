from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "Word Exam Bank"


settings = Settings()

