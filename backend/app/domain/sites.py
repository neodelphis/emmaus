from __future__ import annotations

from dataclasses import dataclass

from app.domain.errors import DomainError


@dataclass(frozen=True)
class SiteInfo:
    code: str
    name: str


SITES: tuple[SiteInfo, ...] = (
    SiteInfo(code="vaire", name="Vairé"),
    SiteInfo(code="les-essarts", name="Les Essarts"),
)
DEFAULT_SITE = SITES[0].code
SITE_BY_CODE = {site.code: site for site in SITES}
SITE_CODES = tuple(SITE_BY_CODE)


def site_name(code: str) -> str:
    site = SITE_BY_CODE.get(code)
    return site.name if site else code


def ensure_known_site(code: str) -> str:
    if code not in SITE_BY_CODE:
        raise DomainError("Site inconnu.", status_code=422)
    return code
