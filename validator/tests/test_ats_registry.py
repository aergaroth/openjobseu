import pytest
from app.adapters.ats.registry import register, get_adapter, list_providers


class DummyAdapter:
    pass


def test_registry_list_and_get():
    register("dummy", DummyAdapter)
    providers = list_providers()
    assert "dummy" in providers

    adapter = get_adapter("dummy")
    assert isinstance(adapter, DummyAdapter)

    # Sprawdzenie odporności na spacje i wielkość liter
    assert isinstance(get_adapter(" DUMMY "), DummyAdapter)


def test_get_adapter_unknown():
    with pytest.raises(ValueError, match="Unknown ATS provider: unknown"):
        get_adapter("unknown")


def test_get_adapter_none():
    with pytest.raises(ValueError, match="Unknown ATS provider: None"):
        get_adapter(None)
