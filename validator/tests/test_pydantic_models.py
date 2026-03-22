import importlib
import pkgutil

from pydantic import BaseModel

import app


def import_submodules(package):
    """
    Rekurencyjnie importuje wszystkie submoduły w danej paczce.
    Jest to konieczne, aby Python 'zauważył' wszystkie definicje klas i załadował
    je do pamięci przed wywołaniem __subclasses__().
    """
    for _, name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        try:
            importlib.import_module(name)
        except Exception:
            # Ignorujemy błędy importu pojedynczych skryptów (np. narzędziowych),
            # skupiamy się na głównych strukturach aplikacji.
            pass


def test_all_pydantic_models_forbid_extra():
    import_submodules(app)

    def get_all_subclasses(cls):
        all_subclasses = set(cls.__subclasses__())
        for subclass in cls.__subclasses__():
            all_subclasses.update(get_all_subclasses(subclass))
        return all_subclasses

    failing_models = []

    # Modele wyłączone z reguły (np. takie, które celowo przyjmują nieznane payloady od zewnętrznych API)
    whitelist = {
        # "app.api.tasks.TaskExecuteResponse",
    }

    for model in get_all_subclasses(BaseModel):
        if not model.__module__.startswith("app."):
            continue

        full_name = f"{model.__module__}.{model.__name__}"
        if full_name not in whitelist and model.model_config.get("extra") != "forbid":
            failing_models.append(full_name)

    assert not failing_models, f"Znaleziono modele Pydantic bez 'extra=\"forbid\"': {failing_models}"
