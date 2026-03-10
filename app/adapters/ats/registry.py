ATS_REGISTRY = {}


def register(provider, adapter_cls):
    ATS_REGISTRY[provider.lower()] = adapter_cls


def get_adapter(provider):

    key = (provider or "").lower().strip()

    adapter_cls = ATS_REGISTRY.get(key)

    if not adapter_cls:
        raise ValueError(f"Unknown ATS provider: {provider}")

    return adapter_cls()


def list_providers():
    return list(ATS_REGISTRY.keys())
