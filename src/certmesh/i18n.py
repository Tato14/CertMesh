"""Language detection + localisation.

CertMesh processes requests and responds in the learner/manager's language. We
support English, Catalan and Spanish as first-class (the contest brief's
minimum) and detect "other" languages so they can be handled safely.

Detection uses a small, transparent stopword/diacritic heuristic tuned to
separate the ca/es/en triad (which generic detectors confuse on short inputs),
and falls back to ``langdetect`` for anything outside the triad. The offline
localisation tables below let the agents produce learner-facing labels in the
detected language even with no model available (the repository itself stays in
English).
"""

from __future__ import annotations

import re

SUPPORTED = ("en", "ca", "es")

# Distinctive tokens. The ca/es pairs are deliberately the ones that *differ*
# between the two languages so the heuristic can tell them apart.
_MARKERS: dict[str, list[str]] = {
    "ca": [
        "amb", "què", "aquest", "aquesta", "molt", "tinc", "vull", "fer",
        "estudiar", "examen", "certificació", "preparar", "necessito",
        "el meu", "la meva", "rol", "hores", "setmana", "també", "per a",
    ],
    "es": [
        "con", "que", "muy", "tengo", "quiero", "hacer", "estudiar", "examen",
        "certificación", "preparar", "necesito", "mi", "rol", "horas", "semana",
        "también", "para", "cómo", "puedo",
    ],
    "en": [
        "the", "and", "with", "want", "study", "exam", "certification", "prepare",
        "need", "role", "hours", "week", "how", "can", "ready", "team", "for",
    ],
}


def _score(text: str, markers: list[str]) -> int:
    score = 0
    for m in markers:
        if " " in m:
            score += 2 * len(re.findall(re.escape(m), text))
        else:
            score += len(re.findall(rf"(?<![a-z]){re.escape(m)}(?![a-z])", text))
    return score


def detect_language(text: str, hint: str | None = None) -> str:
    """Return an ISO 639-1 code. Honours a valid explicit hint."""
    if hint and hint.lower() in SUPPORTED:
        return hint.lower()
    low = text.lower()
    scores = {lang: _score(low, markers) for lang, markers in _MARKERS.items()}
    best = max(scores, key=lambda k: scores[k])
    if scores[best] > 0:
        # Resolve ca/es ties by a couple of decisive diacritics/tokens.
        if scores["ca"] == scores["es"] and scores["ca"] > 0:
            if "·" in text or "tinc" in low or "vull" in low or "què" in low:
                return "ca"
            return "es"
        return best
    # Very short fragments are unreliable for any detector — default to English.
    if len(text.split()) < 3:
        return "en"
    try:  # pragma: no cover - exercised only when langdetect is installed
        from langdetect import detect  # type: ignore

        code = detect(text).split("-")[0]
        # Only trust the generic detector for the non-English triad members; for
        # anything else (incl. its frequent short-English misfires like "no"),
        # fall back to English, our lingua franca for the supported triad.
        return code if code in ("ca", "es") else "en"
    except Exception:
        return "en"


# ── Offline localisation tables ────────────────────────────────────────────────
_STRINGS: dict[str, dict[str, str]] = {
    "band.ready": {"en": "ready", "ca": "preparat", "es": "preparado"},
    "band.borderline": {"en": "borderline", "ca": "al límit", "es": "en el límite"},
    "band.not_ready": {"en": "not ready", "ca": "no preparat", "es": "no preparado"},
    "assess.rationale": {
        "en": "Estimated readiness {score} vs pass threshold {thr} → {band}. Based on {n} grounded practice questions.",
        "ca": "Preparació estimada {score} enfront del llindar d'aprovat {thr} → {band}. Basat en {n} preguntes de pràctica fonamentades.",
        "es": "Preparación estimada {score} frente al umbral de aprobado {thr} → {band}. Basado en {n} preguntas de práctica fundamentadas.",
    },
    "assess.next_advance": {
        "en": "Recommend advancing to {next}.",
        "ca": "Es recomana avançar cap a {next}.",
        "es": "Se recomienda avanzar a {next}.",
    },
    "assess.next_met": {
        "en": "Role certification requirements met — recommend a refresher cycle.",
        "ca": "Els requisits de certificació del rol s'han assolit — es recomana un cicle de repàs.",
        "es": "Se cumplen los requisitos de certificación del rol — se recomienda un ciclo de repaso.",
    },
    "assess.next_continue": {
        "en": "Continue the study plan; prioritise the lowest-scoring skill areas before booking the exam.",
        "ca": "Continueu el pla d'estudi; prioritzeu les àrees amb pitjor puntuació abans de reservar l'examen.",
        "es": "Continúe el plan de estudio; priorice las áreas con peor puntuación antes de reservar el examen.",
    },
    "ai_disclosure": {
        "en": "You are interacting with an AI assistant. Recommendations are decision-support; a manager or learning lead has final oversight.",
        "ca": "Esteu interactuant amb un assistent d'IA. Les recomanacions són de suport a la decisió; un responsable té la supervisió final.",
        "es": "Está interactuando con un asistente de IA. Las recomendaciones son de apoyo a la decisión; un responsable tiene la supervisión final.",
    },
    "review_banner": {
        "en": "Human review recommended",
        "ca": "Es recomana revisió humana",
        "es": "Se recomienda revisión humana",
    },
    "readiness.ready": {
        "en": "READY — practice performance is at or above the pass threshold",
        "ca": "PREPARAT — el rendiment a la pràctica és igual o superior al llindar d'aprovat",
        "es": "PREPARADO — el rendimiento en la práctica iguala o supera el umbral de aprobado",
    },
    "readiness.borderline": {
        "en": "BORDERLINE — close to the threshold; a focused review is advised before booking the exam",
        "ca": "AL LÍMIT — a prop del llindar; es recomana un repàs abans de reservar l'examen",
        "es": "EN EL LÍMITE — cerca del umbral; se aconseja un repaso antes de reservar el examen",
    },
    "readiness.not_ready": {
        "en": "NOT READY — below the pass threshold; continue the study plan before attempting the exam",
        "ca": "NO PREPARAT — per sota del llindar; continueu el pla d'estudi abans d'intentar l'examen",
        "es": "NO PREPARADO — por debajo del umbral; continúe el plan de estudio antes de intentar el examen",
    },
    "summary.path": {
        "en": "Learning path for {cert} aligned to the {role} role, grounded in approved sources.",
        "ca": "Itinerari d'aprenentatge per a {cert} alineat amb el rol {role}, fonamentat en fonts aprovades.",
        "es": "Itinerario de aprendizaje para {cert} alineado con el rol {role}, basado en fuentes aprobadas.",
    },
    "abstain.unknown_cert": {
        "en": "That certification is not in the approved knowledge base, so no grounded plan can be produced. Please pick a supported certification or escalate for manual curation.",
        "ca": "Aquesta certificació no és a la base de coneixement aprovada, així que no es pot generar un pla fonamentat. Trieu una certificació admesa o sol·liciteu revisió manual.",
        "es": "Esa certificación no está en la base de conocimiento aprobada, así que no se puede generar un plan fundamentado. Elija una certificación admitida o solicite revisión manual.",
    },
    "abstain.policy": {
        "en": "This request asks the assistant to ignore its rules or to expose individual records, so it was declined and flagged for review. No agents were run.",
        "ca": "Aquesta petició demana a l'assistent que ignori les seves normes o que exposi registres individuals; s'ha rebutjat i marcat per a revisió. No s'ha executat cap agent.",
        "es": "Esta petición pide al asistente ignorar sus normas o exponer registros individuales; se ha rechazado y marcado para revisión. No se ha ejecutado ningún agente.",
    },
    "abstain.ambiguous": {
        "en": "The goal is ambiguous. Please tell me which certification you are targeting (e.g. AZ-204) or your role.",
        "ca": "L'objectiu és ambigu. Indiqueu quina certificació voleu obtenir (p. ex. AZ-204) o el vostre rol.",
        "es": "El objetivo es ambiguo. Indique qué certificación desea obtener (p. ej. AZ-204) o su rol.",
    },
    "reminder.next": {
        "en": "Next study reminder: {day} at {time} ({slot}).",
        "ca": "Proper recordatori d'estudi: {day} a les {time} ({slot}).",
        "es": "Próximo recordatorio de estudio: {day} a las {time} ({slot}).",
    },
}


def t(key: str, lang: str, **kwargs: str) -> str:
    """Localised string lookup with English fallback and ``str.format`` kwargs."""
    table = _STRINGS.get(key, {})
    template = table.get(lang) or table.get("en") or key
    try:
        return template.format(**kwargs) if kwargs else template
    except (KeyError, IndexError):
        return template


def readiness_label(band: str, lang: str) -> str:
    return t(f"readiness.{band}", lang)
