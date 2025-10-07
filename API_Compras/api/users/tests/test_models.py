import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

User = get_user_model()


@pytest.mark.django_db
def test_save_lowercases_and_full_name_titlecase():
    """Verifica que save() normaliza (lowercase) campos y full_name() title-cases el nombre completo."""
    u = User.objects.create(username="AliceUser", email="ALICE@EXAMPLE.COM",
                            first_name="Alice", last_name="McDonald", password="pwd")
    # refresh para asegurarnos del estado en DB
    u.refresh_from_db()
    assert u.username == "aliceuser"
    assert u.email == "alice@example.com"
    assert u.first_name == "alice"
    assert u.last_name == "mcdonald"
    # full_name debe title-case
    assert u.full_name() == "Alice Mcdonald"


@pytest.mark.django_db
def test_full_name_returns_na_when_no_names():
    """Si first_name y last_name están vacíos, full_name() debe devolver 'N/A'."""
    u = User.objects.create(username="nouser", email="nouser@example.com",
                            first_name="", last_name="", password="pwd")
    u.refresh_from_db()
    assert u.first_name == ""
    assert u.last_name == ""
    assert u.full_name() == "N/A"


@pytest.mark.django_db
def test_unique_username_and_email_constraints_case_insensitive():
    """Verifica que las constraints únicas para username y email se aplican (save lowercasing evita colisiones por case).

    Usamos transaction.atomic() para que IntegrityError no deje la transacción en mal estado.
    """
    User.objects.create(
        username="userx", email="ux@example.com", password="pwd")
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            # mismo username con distinto case -> tras save() queda igual y debe violar unique
            User.objects.create(
                username="UserX", email="ux2@example.com", password="pwd")

    User.objects.create(
        username="usery", email="uy@example.com", password="pwd")
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            # mismo email distinto case
            User.objects.create(username="usery2",
                                email="UY@EXAMPLE.COM", password="pwd")
