from app.config import settings


def test_settings_default_app_name() -> None:
    assert settings.app_name == "orcamento-ai"

