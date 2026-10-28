"""Soru veri modelleri."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

QUESTION_TYPES = {
    "coktan_secmeli": "Kavram (çoktan seçmeli)",
    "kod_ciktisi": "Kod çıktısı tahmini",
    "hata_bulma": "Hatalı satırı bulma",
}

LEVELS = {
    "baslangic": "Başlangıç (9-12 yaş): print, değişken, input, basit if, for/range",
    "orta": "Orta (13-15 yaş): döngüler, listeler, fonksiyonlar, string metotları, sözlükler",
    "ileri": "İleri (16-18 yaş): list comprehension, sınıflar, hata yakalama, modüller, temel veri/YZ kavramları",
}


@dataclass
class Question:
    tur: str
    soru: str
    secenekler: list[str]
    dogru_cevap: str
    aciklama: str
    kod: str | None = None
    zorluk: str = "orta"
    # Doğrulama sonucu (validator doldurur)
    gecerli: bool | None = None
    sorunlar: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Question":
        return cls(
            tur=str(data.get("tur", "")),
            soru=str(data.get("soru", "")).strip(),
            secenekler=[str(s) for s in data.get("secenekler", [])],
            dogru_cevap=str(data.get("dogru_cevap", "")),
            aciklama=str(data.get("aciklama", "")).strip(),
            kod=(data.get("kod") or None),
            zorluk=str(data.get("zorluk", "orta")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuestionSet:
    konu: str
    seviye: str
    sorular: list[Question]
    model: str = ""
    onarim_turu: int = 0  # Kaç soru Claude'a geri gönderilip düzeltildi

    @property
    def gecerli_sayisi(self) -> int:
        return sum(1 for q in self.sorular if q.gecerli)

    def to_dict(self) -> dict[str, Any]:
        return {
            "konu": self.konu,
            "seviye": self.seviye,
            "model": self.model,
            "onarim_turu": self.onarim_turu,
            "sorular": [q.to_dict() for q in self.sorular],
        }
