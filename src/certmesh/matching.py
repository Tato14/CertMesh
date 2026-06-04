"""Deterministic, language-agnostic text folding + concept matching.

A small utility shared by the grounding machinery. ``fold`` (used by
``iq/foundry_iq``) normalises text to a lowercase, accent-stripped form so that
the critic's citation-grounding check and the BM25 retriever are robust across
English, Catalan and Spanish without any LLM call — which is why citation
grounding can be enforced as a hard CI gate even in fully offline mode.

Key idea: folding preserves character indices, so an evidence span found in
folded text maps straight back onto the original text for UI highlighting.
"""

from __future__ import annotations

import re
import unicodedata

from .schemas import EvidenceSpan


def _fold_char(ch: str) -> str:
    """Lowercase + strip accents for a single char, preserving length (1 char).

    é→e, À→a, ñ→n, ü→u, ç→c. The Catalan interpunct '·' and punctuation are
    passed through; the matcher treats them as non-word separators.
    """
    lower = ch.lower()
    decomposed = unicodedata.normalize("NFKD", lower)
    base = "".join(c for c in decomposed if not unicodedata.combining(c))
    if not base:
        return lower
    return base[0]


def fold(text: str) -> str:
    """Fold text to a lowercase, accent-free string of the SAME length.

    Index ``i`` of the result corresponds to index ``i`` of the input, so
    offsets found in folded text are valid offsets in the original.
    """
    return "".join(_fold_char(c) for c in text)


def _synonym_pattern(synonym: str) -> re.Pattern[str]:
    """Compile a word-boundary-aware regex for a folded synonym.

    Internal whitespace becomes flexible (``\\s+``) and the Catalan interpunct
    is tolerated, so "al·lucinacio" and "allucinacio" both match a spelling
    with the middot folded out. Boundaries are alphanumeric so 'esforc' does
    not match inside 'esforcat' unintentionally beyond word edges.
    """
    folded = fold(synonym).strip()
    # Tokens may be separated by whitespace, the Catalan interpunct, semicolons,
    # apostrophes or hyphens. Treating all of these as flexible separators lets
    # Catalan/Spanish contractions match across variants — e.g. "treure's la
    # vida" and "treure-s la vida", or "non-healing" / "non healing".
    sep = r"[\s·;'’‘’\-]+"
    parts = [p for p in re.split(sep, folded) if p]
    escaped = sep.join(re.escape(p) for p in parts)
    if not escaped:
        return re.compile(r"(?!x)x")  # never matches
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


# Synonym patterns are static; cache compiled regexes across the whole run.
_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _pattern_for(synonym: str) -> re.Pattern[str]:
    pat = _PATTERN_CACHE.get(synonym)
    if pat is None:
        pat = _synonym_pattern(synonym)
        _PATTERN_CACHE[synonym] = pat
    return pat


def find_concept(note: str, synonyms: list[str]) -> EvidenceSpan | None:
    """Return the first evidence span where any synonym of a concept appears.

    ``note`` is the original (display) text; matching is done on its folded
    form. The returned span's ``text`` is the verbatim slice from the original
    text so the UI can highlight the user's own words.
    """
    folded_note = fold(note)
    best: tuple[int, int] | None = None
    for syn in synonyms:
        m = _pattern_for(syn).search(folded_note)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), m.end())
    if best is None:
        return None
    start, end = best
    return EvidenceSpan(text=note[start:end], start=start, end=end, field="note")


def concept_present(note: str, synonyms: list[str]) -> bool:
    return find_concept(note, synonyms) is not None


def any_keyword_span(note: str, synonyms: list[str]) -> EvidenceSpan | None:
    """Alias used by routing — same as find_concept, named for readability."""
    return find_concept(note, synonyms)
