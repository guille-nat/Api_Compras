import pytest
from api.constants import NotificationCodes, EmailSettings


def test_notification_codes_and_email_settings():
    """Verifica constantes públicas y helpers simples."""
    # valores esperados mínimos
    assert NotificationCodes.PURCHASE_CONFIRMED in NotificationCodes.ALL_CODES
    choices = NotificationCodes.get_choices()
    assert any(t[0] == NotificationCodes.PURCHASE_CONFIRMED for t in choices)

    # email settings basic sanity
    assert isinstance(EmailSettings.DEFAULT_FROM_EMAIL, str)
    assert EmailSettings.EMAIL_TIMEOUT > 0
