"""A Build Doctor szerződése: ezt adja vissza minden agent-implementáció. NE módosítsd a mezőket
(az n8n flow és az eval erre épít) – bővíteni lehet, de akkor frissítsd a docs/SPEC.md-t is.
A 2. szintű mezők (culprit_commit, fix_patch, fix_verified) opcionálisak: a baseline nem tölti ki őket."""
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["dependency", "flaky_test", "type_error", "config", "timeout", "code_bug", "unknown"]


class Evidence(BaseModel):
    file: str = Field(description="Repó-relatív útvonal, pl. telemetry/units.py vagy requirements.txt")
    line: int = Field(description="1-től számozott sor a fájlban, a futás állapotában")
    quote: str = Field(description="A releváns sor (vagy log-sor) szó szerint")


class Diagnosis(BaseModel):
    run_id: str
    category: Category
    root_cause: str = Field(description="1-3 mondat: mi okozza a hibát")
    evidence: list[Evidence] = Field(default_factory=list, description="Legalább 1 elem, különben category=unknown")
    suggested_fix: str = Field(description="Konkrét javaslat; diff-részlet is lehet")
    confidence: float = Field(ge=0, le=1)
    needs_human: bool = Field(description="True, ha emberi döntés kell (bizonytalan, gyanús tartalom, mellékhatás)")
    security_notes: str = Field(default="", description="Ha a logban/commitban/fájlban gyanús utasítás volt, itt jelezd")
    # --- 2. szint -------------------------------------------------------------------------------------------
    culprit_commit: str | None = Field(default=None, description="A hibát BEHOZÓ commit sha-ja (legalább 7 karakter). "
                                       "Nem mindig a fejcommit: nézd meg a futás összes új commitját.")
    fix_patch: str | None = Field(default=None, description="Unified diff (a/ és b/ előtaggal) – CSAK ha verify_patch-csel "
                                  "ellenőrizted és tests_ok volt; különben null. Tesztfájlt nem módosíthat.")
    fix_verified: bool = Field(default=False, description="True, ha a fix_patch-et verify_patch-csel ellenőrizted és zöld lett")


@dataclass
class Trace:
    """Mit csinált az agent – az eval és a demó ebből dolgozik."""
    impl: str
    model: str = ""
    steps: int = 0
    tool_calls: list[dict] = field(default_factory=list)   # {"name", "args", "ok"}
    tokens_in: int = 0
    tokens_out: int = 0
    duration_s: float = 0.0
    notes: list[str] = field(default_factory=list)

    def called(self, *names: str) -> bool:
        return any(c["name"] in names for c in self.tool_calls)
