from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "7514886"


@pytest.fixture(scope="session")
def fx():
    """Lê um fixture HTML da coleta real de 14/09/2026 (bytes brutos, como vieram do portal)."""
    def _load(nome: str) -> bytes:
        return (FIXTURES / f"{nome}.html").read_bytes()
    return _load
