"""Soru setini öğrenci sayfası ve cevap anahtarı olarak dışa aktarır."""

from __future__ import annotations

import json

from .models import LEVELS, QuestionSet

HARFLER = "ABCD"


def _kod_blogu(kod: str, satir_no: bool) -> str:
    if satir_no:
        kod = "\n".join(f"{i:>2} | {s}" for i, s in enumerate(kod.splitlines(), 1))
    return f"```python\n{kod}\n```"


def to_markdown(qs: QuestionSet, cevap_anahtari: bool = True) -> str:
    seviye = LEVELS.get(qs.seviye, qs.seviye).split(":")[0]
    out = [f"# {qs.konu} — Python Soruları", f"**Seviye:** {seviye}  ", "**Ad Soyad:** ____________", ""]
    for i, q in enumerate(qs.sorular, 1):
        out.append(f"### {i}. {q.soru}")
        if q.kod:
            out.append(_kod_blogu(q.kod, satir_no=q.tur == "hata_bulma"))
        for harf, secenek in zip(HARFLER, q.secenekler):
            secenek = secenek.replace("\n", " ⏎ ")
            out.append(f"- **{harf})** `{secenek}`" if q.tur == "kod_ciktisi" else f"- **{harf})** {secenek}")
        out.append("")

    if cevap_anahtari:
        out += ["---", "## Cevap Anahtarı", ""]
        for i, q in enumerate(qs.sorular, 1):
            temiz = [s.strip() for s in q.secenekler]
            harf = HARFLER[temiz.index(q.dogru_cevap.strip())] if q.dogru_cevap.strip() in temiz else "?"
            out.append(f"**{i}. {harf}** — {q.aciklama}")
            out.append("")
    return "\n".join(out)


def to_json(qs: QuestionSet) -> str:
    return json.dumps(qs.to_dict(), ensure_ascii=False, indent=2)
