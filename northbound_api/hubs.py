"""The hubs Northbound Dispatch runs line haul between."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Hub:
    code: str
    name: str
    country: str
    lat: float
    lon: float


HUBS: dict[str, Hub] = {
    h.code: h
    for h in (
        Hub("HEL", "Helsinki", "FI", 60.1699, 24.9384),
        Hub("TKU", "Turku", "FI", 60.4518, 22.2666),
        Hub("TMP", "Tampere", "FI", 61.4978, 23.7610),
        Hub("OUL", "Oulu", "FI", 65.0121, 25.4651),
        Hub("RVN", "Rovaniemi", "FI", 66.5039, 25.7294),
        Hub("TLL", "Tallinn", "EE", 59.4370, 24.7536),
        Hub("STO", "Stockholm", "SE", 59.3293, 18.0686),
        Hub("TOS", "Tromsø", "NO", 69.6492, 18.9553),
    )
}


class UnknownHub(KeyError):
    """Raised when a hub code is not in the network."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def get_hub(code: str) -> Hub:
    try:
        return HUBS[code.upper()]
    except KeyError:
        raise UnknownHub(code) from None
