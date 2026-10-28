"""Claude API ile soru üretimi.

Akış:
1. Claude'a seviye, konu ve soru türleri verilir.
2. Claude cevabını serbest metin yerine `soru_setini_kaydet` aracı (tool use)
   üzerinden, JSON şemasına uyan yapılandırılmış veri olarak döner.
3. Her soru otomatik doğrulanır (kod gerçekten çalıştırılır).
4. Doğrulamayı geçemeyen sorular, bulunan sorunlarla birlikte Claude'a geri
   gönderilir ve düzeltilmesi istenir (en fazla `max_onarim` tur).
"""

from __future__ import annotations

import os
from typing import Any, Callable

from .models import LEVELS, QUESTION_TYPES, Question, QuestionSet
from .validator import validate_question

DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
TOOL_NAME = "soru_setini_kaydet"

SORU_SEMASI: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tur": {"type": "string", "enum": list(QUESTION_TYPES)},
        "soru": {"type": "string", "description": "Öğrenciye gösterilecek soru metni (Türkçe)."},
        "kod": {
            "type": "string",
            "description": "kod_ciktisi ve hata_bulma için Python kodu. coktan_secmeli için boş bırakılabilir.",
        },
        "secenekler": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 4,
            "maxItems": 4,
            "description": "Tam 4 benzersiz seçenek.",
        },
        "dogru_cevap": {
            "type": "string",
            "description": "Seçeneklerden biriyle birebir aynı olmalı.",
        },
        "aciklama": {"type": "string", "description": "Doğru cevabın öğrenciye uygun kısa açıklaması."},
        "zorluk": {"type": "string", "enum": ["kolay", "orta", "zor"]},
    },
    "required": ["tur", "soru", "secenekler", "dogru_cevap", "aciklama", "zorluk"],
}

TOOLS = [
    {
        "name": TOOL_NAME,
        "description": "Üretilen Python soru setini yapılandırılmış biçimde kaydeder.",
        "input_schema": {
            "type": "object",
            "properties": {"sorular": {"type": "array", "items": SORU_SEMASI}},
            "required": ["sorular"],
        },
    }
]

SYSTEM_PROMPT = """Sen çocuklara ve gençlere Python öğreten deneyimli bir eğitmensin.
Görevin, verilen seviye ve konuya uygun, ölçme değeri yüksek sorular hazırlamak.

Kurallar:
- Dil Türkçe, sade ve yaşa uygun olsun. Değişken adları anlamlı ve Türkçe karakter içermesin.
- Her soruda tam 4 benzersiz seçenek olsun; `dogru_cevap` seçeneklerden biriyle birebir aynı olsun.
- Çeldiriciler öğrencilerin gerçekten yaptığı hatalardan gelsin (ör. range sonunu dahil sanmak, = ile == karışıklığı).
- kod_ciktisi: Kod en fazla 10 satır, input() kullanmasın, rastgelelik içermesin.
  `dogru_cevap` kodun TAM ekran çıktısı olsun (birden çok satırsa satır sonlarıyla).
- hata_bulma: 6-10 satırlık kod yaz ve tam olarak BİR satıra, çalıştırınca Python'un hata
  vereceği bir hata koy (SyntaxError, NameError, TypeError, IndexError vb.).
  Seçenekler satır numaraları olsun (ör. "3"), `dogru_cevap` hatalı satırın numarası olsun.
- coktan_secmeli: Kavram sorusu; kısa kod parçası içerebilir.
- Dosya, işletim sistemi, ağ işlemi veya import os/subprocess kullanma.
- Sonucu mutlaka `soru_setini_kaydet` aracıyla döndür."""


def build_prompt(konu: str, seviye: str, turler: list[str], adet: int) -> str:
    tur_listesi = ", ".join(f"{t} ({QUESTION_TYPES[t]})" for t in turler)
    return (
        f"Seviye: {LEVELS.get(seviye, seviye)}\n"
        f"Konu: {konu}\n"
        f"Soru türleri: {tur_listesi}\n"
        f"Toplam {adet} soru üret; türleri dengeli dağıt ve zorluğu kolaydan zora sırala."
    )


def build_repair_prompt(hatali: list[Question]) -> str:
    satirlar = ["Aşağıdaki sorular otomatik doğrulamadan geçemedi. Her birini aynı tür ve konuda düzelt:"]
    for i, q in enumerate(hatali, 1):
        satirlar.append(f"\n{i}. Soru: {q.soru}")
        if q.kod:
            satirlar.append(f"Kod:\n{q.kod}")
        satirlar.append(f"Verilen cevap: {q.dogru_cevap!r}")
        satirlar.append("Sorunlar: " + " | ".join(q.sorunlar))
    satirlar.append(f"\nTam {len(hatali)} düzeltilmiş soruyu aynı sırayla döndür.")
    return "\n".join(satirlar)


class QuestionGenerator:
    def __init__(self, client: Any | None = None, model: str = DEFAULT_MODEL, max_onarim: int = 2):
        if client is None:
            import anthropic

            client = anthropic.Anthropic()  # ANTHROPIC_API_KEY ortam değişkenini okur
        self.client = client
        self.model = model
        self.max_onarim = max_onarim

    def _call(self, messages: list[dict[str, Any]]) -> tuple[list[Question], Any]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=messages,
        )
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == TOOL_NAME:
                return [Question.from_dict(d) for d in block.input.get("sorular", [])], response
        raise RuntimeError("Claude beklenen araç çağrısını döndürmedi.")

    def generate(
        self,
        konu: str,
        seviye: str = "baslangic",
        turler: list[str] | None = None,
        adet: int = 5,
        on_progress: Callable[[str], None] | None = None,
    ) -> QuestionSet:
        turler = turler or list(QUESTION_TYPES)
        log = on_progress or (lambda _msg: None)

        log("Claude soruları hazırlıyor…")
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": build_prompt(konu, seviye, turler, adet)}
        ]
        sorular, _ = self._call(messages)

        log("Sorular doğrulanıyor (kodlar çalıştırılıyor)…")
        for q in sorular:
            validate_question(q)

        onarilan = 0
        for tur in range(1, self.max_onarim + 1):
            hatali_idx = [i for i, q in enumerate(sorular) if not q.gecerli]
            if not hatali_idx:
                break
            log(f"{len(hatali_idx)} soru hatalı, Claude'a düzelttiriliyor (tur {tur})…")
            hatali = [sorular[i] for i in hatali_idx]
            duzeltilmis, _ = self._call(
                [{"role": "user", "content": build_repair_prompt(hatali)}]
            )
            for i, yeni in zip(hatali_idx, duzeltilmis):
                validate_question(yeni)
                sorular[i] = yeni
                onarilan += 1

        return QuestionSet(konu=konu, seviye=seviye, sorular=sorular, model=self.model, onarim_turu=onarilan)
