"""Contrôle de santé des flux RSS du registre.

Usage :
    python -m src.ingestion.check_feeds
    python -m src.ingestion.check_feeds --config config/sources.yaml --sortie data/source_health.json

Le YAML n'est jamais réécrit : il reste édité à la main (et garde ses
commentaires). Les résultats vont dans un fichier JSON séparé.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import httpx

from src.ingestion.sources import Source, charger_registre

USER_AGENT = (
    "ai-newsops-platform/0.2 (projet portfolio de veille presse ; "
    "+https://github.com/Artificial-Intelligence-Architect/ai-newsops-platform)"
)
TIMEOUT_S = 15.0
PAUSE_ENTRE_REQUETES_S = 1.0  # politesse envers les serveurs


@dataclass
class ResultatFlux:
    nom: str
    url: str
    verdict: (
        str  # ok | ok_avec_avertissement | vide | invalide | erreur_http | injoignable
    )
    http_status: int | None
    nb_entrees: int
    bozo: bool
    detail: str | None
    duree_ms: int
    teste_le: str


def evaluer(contenu: bytes) -> tuple[str, int, bool, str | None]:
    """Analyse le contenu d'un flux. Retourne (verdict, nb_entrees, bozo, detail).

    Séparée du réseau pour pouvoir être testée sans connexion.
    """
    d = feedparser.parse(contenu)
    nb = len(d.entries)
    bozo = bool(d.bozo)
    detail = str(d.get("bozo_exception")) if bozo else None
    if nb > 0:
        # feedparser signale parfois des défauts bénins (encodage...) sur des
        # flux parfaitement lisibles : on les garde, avec un avertissement.
        return ("ok_avec_avertissement" if bozo else "ok"), nb, bozo, detail
    return ("invalide" if bozo else "vide"), 0, bozo, detail


def verifier(source: Source, client: httpx.Client) -> ResultatFlux:
    debut = time.monotonic()
    maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        r = client.get(source.url)
    except httpx.HTTPError as e:
        return ResultatFlux(
            source.nom,
            source.url,
            "injoignable",
            None,
            0,
            False,
            f"{type(e).__name__}: {e}",
            int((time.monotonic() - debut) * 1000),
            maintenant,
        )
    duree = int((time.monotonic() - debut) * 1000)
    if r.status_code >= 400:
        return ResultatFlux(
            source.nom,
            source.url,
            "erreur_http",
            r.status_code,
            0,
            False,
            None,
            duree,
            maintenant,
        )
    verdict, nb, bozo, detail = evaluer(r.content)
    return ResultatFlux(
        source.nom,
        source.url,
        verdict,
        r.status_code,
        nb,
        bozo,
        detail,
        duree,
        maintenant,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Teste tous les flux du registre.")
    parser.add_argument("--config", default="config/sources.yaml")
    parser.add_argument("--sortie", default="data/source_health.json")
    args = parser.parse_args()

    registre = charger_registre(args.config)
    a_tester = [s for s in registre.sources if s.url is not None]
    print(
        f"{len(a_tester)} flux à tester ({len(registre.sources)} sources au registre)\n"
    )

    resultats: list[ResultatFlux] = []
    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S, follow_redirects=True
    ) as client:
        for i, source in enumerate(a_tester):
            if i > 0:
                time.sleep(PAUSE_ENTRE_REQUETES_S)
            res = verifier(source, client)
            resultats.append(res)
            print(f"{res.verdict:<22} {res.nb_entrees:>4} entrées  {res.nom}")

    sortie = Path(args.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(
        json.dumps([asdict(r) for r in resultats], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    nb_ok = sum(r.verdict.startswith("ok") for r in resultats)
    print(f"\n{nb_ok}/{len(resultats)} flux exploitables. Détail : {sortie}")


if __name__ == "__main__":
    main()
