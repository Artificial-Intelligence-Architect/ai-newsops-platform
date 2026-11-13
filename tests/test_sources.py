"""Tests du registre des sources et de l'évaluation des flux (sans réseau)."""

import httpx
import pytest
from pydantic import ValidationError

from src.ingestion.check_feeds import evaluer, verifier
from src.ingestion.sources import Registre, Source, charger_registre

SOURCE_MINIMALE = {
    "nom": "Exemple",
    "langue": "fr",
    "pays": "FR",
    "type_source": "presse_generaliste",
    "url": "https://exemple.fr/rss.xml",
    "statut_verification": "confirme",
}

FLUX_VALIDE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>Article 1</title><link>https://exemple.fr/1</link></item>
<item><title>Article 2</title><link>https://exemple.fr/2</link></item>
</channel></rss>"""


# --- Le vrai registre du projet -------------------------------------------


def test_le_registre_du_projet_est_valide():
    registre = charger_registre("config/sources.yaml")
    assert len(registre.sources) > 0


# --- Règles de validation ---------------------------------------------------


def test_source_minimale_acceptee():
    Source(**SOURCE_MINIMALE)


def test_url_manquante_refusee_si_statut_confirme():
    with pytest.raises(ValidationError, match="url manquante"):
        Source(**{**SOURCE_MINIMALE, "url": None})


def test_url_manquante_acceptee_si_a_completer():
    Source(**{**SOURCE_MINIMALE, "url": None, "statut_verification": "a_completer"})


def test_statut_inconnu_refuse():
    with pytest.raises(ValidationError):
        Source(**{**SOURCE_MINIMALE, "statut_verification": "valide"})


def test_langue_invalide_refusee():
    with pytest.raises(ValidationError, match="langue invalide"):
        Source(**{**SOURCE_MINIMALE, "langue": "Français"})


def test_espaces_parasites_supprimes():
    s = Source(**{**SOURCE_MINIMALE, "nom": "BBC Health "})
    assert s.nom == "BBC Health"


def test_doublon_de_nom_refuse():
    autre = {**SOURCE_MINIMALE, "url": "https://exemple.fr/autre.xml"}
    with pytest.raises(ValidationError, match="Nom de source en double"):
        Registre(meta={}, sources=[SOURCE_MINIMALE, autre])


def test_doublon_d_url_refuse():
    with pytest.raises(ValidationError, match="URL en double"):
        Registre(
            meta={}, sources=[SOURCE_MINIMALE, {**SOURCE_MINIMALE, "nom": "Copie"}]
        )


# --- Évaluation d'un flux ---------------------------------------------------


def test_flux_valide():
    verdict, nb, bozo, _ = evaluer(FLUX_VALIDE)
    assert (verdict, nb, bozo) == ("ok", 2, False)


def test_page_html_au_lieu_d_un_flux():
    verdict, nb, _, _ = evaluer(b"<html><body>Page introuvable</body></html>")
    assert verdict in ("vide", "invalide")
    assert nb == 0


# --- Interrogation d'un flux, avec un faux serveur (httpx.MockTransport) ----


def _client_qui_repond(status: int, contenu: bytes = b"") -> httpx.Client:
    """Client httpx branché sur un faux serveur : aucun accès réseau."""
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(status, content=contenu)
        )
    )


def test_verifier_flux_ok():
    with _client_qui_repond(200, FLUX_VALIDE) as client:
        res = verifier(Source(**SOURCE_MINIMALE), client)
    assert (res.verdict, res.nb_entrees, res.http_status) == ("ok", 2, 200)


def test_verifier_403_classe_acces_refuse():
    with _client_qui_repond(403) as client:
        res = verifier(Source(**SOURCE_MINIMALE), client)
    assert (res.verdict, res.http_status) == ("acces_refuse", 403)


def test_verifier_404_classe_erreur_http():
    with _client_qui_repond(404) as client:
        res = verifier(Source(**SOURCE_MINIMALE), client)
    assert (res.verdict, res.http_status) == ("erreur_http", 404)


def test_statut_bloque_robot_accepte():
    Source(**{**SOURCE_MINIMALE, "statut_verification": "bloque_robot"})
