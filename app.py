"""Streamlit arayüzü: streamlit run app.py"""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from soru_uretici import QuestionGenerator, QuestionSet, validate_set
from soru_uretici.export import to_json, to_markdown
from soru_uretici.generator import DEFAULT_MODEL
from soru_uretici.models import LEVELS, QUESTION_TYPES, Question

ORNEK = Path(__file__).parent / "examples" / "ornek_soru_seti.json"
HAZIR_KONULAR = [
    "print ve değişkenler",
    "if-else koşulları",
    "for döngüsü ve range",
    "while döngüsü",
    "listeler",
    "fonksiyonlar",
    "sözlükler",
    "string metotları",
    "hata yakalama (try-except)",
    "sınıflar ve nesneler",
]

st.set_page_config(page_title="Claude Soru Üretici", page_icon="🧩", layout="wide")
st.title("🧩 Claude ile Python Soru Üretici")
st.caption("Seviyeye uygun soruları Claude üretir, kod soruları otomatik çalıştırılarak doğrulanır.")

with st.sidebar:
    st.header("Ayarlar")
    api_key = st.text_input(
        "Anthropic API anahtarı",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Boş bırakırsan örnek soru seti gösterilir.",
    )
    model = st.text_input("Model", value=DEFAULT_MODEL)
    seviye = st.selectbox("Seviye", list(LEVELS), format_func=lambda k: LEVELS[k].split(":")[0])
    konu_secim = st.selectbox("Konu", HAZIR_KONULAR + ["Diğer…"])
    konu = st.text_input("Konu yaz") if konu_secim == "Diğer…" else konu_secim
    turler = st.multiselect(
        "Soru türleri", list(QUESTION_TYPES), default=list(QUESTION_TYPES), format_func=QUESTION_TYPES.get
    )
    adet = st.slider("Soru sayısı", 3, 10, 5)
    uret = st.button("Soruları üret", type="primary", use_container_width=True)

if uret:
    if not turler or not konu:
        st.error("En az bir soru türü ve bir konu seç.")
    elif not api_key:
        st.info("API anahtarı yok, örnek soru seti gösteriliyor.")
        data = json.loads(ORNEK.read_text(encoding="utf-8"))
        qs = QuestionSet(
            konu=data["konu"], seviye=data["seviye"], sorular=[Question.from_dict(q) for q in data["sorular"]],
            model="örnek veri",
        )
        st.session_state["qs"] = validate_set(qs)
    else:
        import anthropic

        durum = st.status("Çalışıyor…", expanded=True)
        try:
            gen = QuestionGenerator(client=anthropic.Anthropic(api_key=api_key), model=model)
            st.session_state["qs"] = gen.generate(konu, seviye, turler, adet, on_progress=durum.write)
            durum.update(label="Hazır", state="complete")
        except anthropic.APIError as e:
            durum.update(label="Hata", state="error")
            st.error(f"Claude API hatası: {e}")

qs: QuestionSet | None = st.session_state.get("qs")
if qs:
    c1, c2, c3 = st.columns(3)
    c1.metric("Soru", len(qs.sorular))
    c2.metric("Doğrulamadan geçen", f"{qs.gecerli_sayisi}/{len(qs.sorular)}")
    c3.metric("Claude'a düzelttirilen", qs.onarim_turu)

    for i, q in enumerate(qs.sorular, 1):
        isaret = "✅" if q.gecerli else "⚠️"
        with st.expander(f"{isaret} {i}. {q.soru}  ·  {QUESTION_TYPES.get(q.tur, q.tur)} · {q.zorluk}"):
            if q.kod:
                st.code(q.kod, language="python", line_numbers=True)
            for harf, s in zip("ABCD", q.secenekler):
                dogru = s.strip() == q.dogru_cevap.strip()
                s = s.replace("\n", " ⏎ ")
                st.markdown(f"{'**' if dogru else ''}{harf}) {s}{' ✔' if dogru else ''}{'**' if dogru else ''}")
            st.caption(f"Açıklama: {q.aciklama}")
            for sorun in q.sorunlar:
                st.warning(sorun)

    d1, d2, d3 = st.columns(3)
    dosya = qs.konu.replace(" ", "_")
    d1.download_button("Öğrenci sayfası (.md)", to_markdown(qs, cevap_anahtari=False), f"{dosya}.md")
    d2.download_button("Cevap anahtarlı (.md)", to_markdown(qs), f"{dosya}_cevapli.md")
    d3.download_button("JSON", to_json(qs), f"{dosya}.json", mime="application/json")
