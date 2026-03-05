ATS_REGISTRY = {}


def register(provider, adapter_cls):
    ATS_REGISTRY[provider] = adapter_cls


def get_adapter(provider):
    adapter = ATS_REGISTRY.get(provider)
    if not adapter:
        raise ValueError(f"Unknown ATS provider: {provider}")
    return adapter
