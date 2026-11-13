"""Registre des sources : chargement et validation de config/sources.yaml.

Le YAML est édité à la main. Ce module vérifie qu'il est cohérent
avant que le reste du pipeline ne l'utilise.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

StatutVerification = Literal[
    "confirme", "a_tester", "a_completer", "en_echec", "bloque_robot"
]
# bloque_robot : l'éditeur refuse la collecte automatisée (HTTP 403, robots.txt).
# On respecte ce refus : ces sources ne sont plus jamais interrogées.


class Source(BaseModel):
    """Une source de presse (un flux RSS)."""

    # Supprime les espaces parasites en début et fin de texte ("BBC Health ").
    model_config = ConfigDict(str_strip_whitespace=True)

    nom: str
    langue: str  # code ISO 639-1 ("fr", "nl"...) ou "multi"
    pays: str  # code pays sur deux lettres ("FR", "BE"...) ou "EU"
    type_source: str
    url: str | None = None
    statut_verification: StatutVerification
    date_verification: date | None = None
    champs_disponibles: list[str] | None = None
    contraintes_licence: str | None = None
    notes: str | None = None

    @field_validator("langue")
    @classmethod
    def langue_valide(cls, v: str) -> str:
        if v != "multi" and not (len(v) == 2 and v.isalpha() and v.islower()):
            raise ValueError(
                f"langue invalide : {v!r} (attendu : 'fr', 'nl'... ou 'multi')"
            )
        return v

    @field_validator("pays")
    @classmethod
    def pays_valide(cls, v: str) -> str:
        if not (len(v) == 2 and v.isalpha() and v.isupper()):
            raise ValueError(f"pays invalide : {v!r} (attendu : 'FR', 'BE'...)")
        return v

    @field_validator("url")
    @classmethod
    def url_http(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError(f"url invalide : {v!r}")
        return v

    @model_validator(mode="after")
    def url_obligatoire_si_testable(self) -> Source:
        # Seules les sources "a_completer" peuvent ne pas avoir d'URL.
        if self.url is None and self.statut_verification != "a_completer":
            raise ValueError(
                f"{self.nom!r} : url manquante alors que le statut est "
                f"{self.statut_verification!r}"
            )
        return self


class Registre(BaseModel):
    """Le fichier sources.yaml complet."""

    meta: dict
    sources: list[Source]

    @model_validator(mode="after")
    def pas_de_doublons(self) -> Registre:
        noms: set[str] = set()
        for s in self.sources:
            if s.nom in noms:
                raise ValueError(
                    f"Nom de source en double dans le registre : {s.nom!r}"
                )
            noms.add(s.nom)
        vues: set[str] = set()
        for s in self.sources:
            if s.url is None:
                continue
            if s.url in vues:
                raise ValueError(f"URL en double dans le registre : {s.url}")
            vues.add(s.url)
        return self


def charger_registre(chemin: str | Path) -> Registre:
    """Lit et valide le YAML. Lève une erreur claire s'il est incohérent."""
    with open(chemin, encoding="utf-8") as f:
        brut = yaml.safe_load(f)
    return Registre.model_validate(brut)
