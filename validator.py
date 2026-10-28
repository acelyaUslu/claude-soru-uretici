"""Claude'un ürettiği soruları otomatik doğrular.

- Her soruda: 4 benzersiz seçenek var mı, doğru cevap seçenekler arasında mı?
- Kod çıktısı sorularında: kod gerçekten çalıştırılır ve çıktı doğru cevapla karşılaştırılır.
- Hata bulma sorularında: işaretlenen satır numarası kodun içinde mi, kod gerçekten hata veriyor mu?

Not: Kod, zaman aşımı olan ayrı bir Python sürecinde, boş bir geçici klasörde
ve izole modda (-I) çalıştırılır. Bu tam bir güvenlik sanal alanı (sandbox)
değildir; üretim ortamında konteyner içinde çalıştırılmalıdır.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile

from .models import Question, QuestionSet

TIMEOUT_SN = 3

# Öğrenci sorularında olmaması gereken, sistemle etkileşen ifadeler
YASAK_IFADELER = ("import os", "import subprocess", "import shutil", "open(", "__import__", "eval(", "exec(")


def run_code(code: str) -> tuple[bool, str, str]:
    """Kodu ayrı süreçte çalıştırır. (başarılı_mı, stdout, stderr) döner."""
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", code],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SN,
                cwd=tmp,
                env={},
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return False, "", "Zaman aşımı"
    return proc.returncode == 0, proc.stdout, proc.stderr


def error_line(stderr: str) -> int | None:
    """Traceback içinden hatanın oluştuğu son satır numarasını bulur."""
    satirlar = re.findall(r'File "<string>", line (\d+)', stderr)
    return int(satirlar[-1]) if satirlar else None


def _normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def validate_question(q: Question) -> Question:
    sorunlar: list[str] = []

    if len(q.secenekler) != 4:
        sorunlar.append(f"4 seçenek olmalı, {len(q.secenekler)} var.")
    if len({_normalize(s) for s in q.secenekler}) != len(q.secenekler):
        sorunlar.append("Seçenekler tekrar ediyor.")
    if _normalize(q.dogru_cevap) not in {_normalize(s) for s in q.secenekler}:
        sorunlar.append("Doğru cevap seçenekler arasında değil.")

    if q.tur in ("kod_ciktisi", "hata_bulma"):
        if not q.kod:
            sorunlar.append("Bu soru türü kod içermeli.")
        elif any(ifade in q.kod for ifade in YASAK_IFADELER):
            sorunlar.append("Kod, öğrenci sorusu için uygun olmayan sistem işlemleri içeriyor.")
        elif q.tur == "kod_ciktisi":
            ok, out, err = run_code(q.kod)
            if not ok:
                sorunlar.append(f"Kod çalışmadı: {err.strip().splitlines()[-1] if err.strip() else 'bilinmeyen hata'}")
            elif _normalize(out) != _normalize(q.dogru_cevap):
                sorunlar.append(
                    f"Gerçek çıktı doğru cevapla uyuşmuyor. Gerçek çıktı: {_normalize(out)!r}"
                )
        elif q.tur == "hata_bulma":
            satir_sayisi = len(q.kod.strip().splitlines())
            try:
                satir = int(str(q.dogru_cevap).strip())
                if not 1 <= satir <= satir_sayisi:
                    sorunlar.append(f"Satır {satir} kodda yok (kod {satir_sayisi} satır).")
            except ValueError:
                sorunlar.append("Hata bulma sorusunda doğru cevap bir satır numarası olmalı.")
            ok, _, err = run_code(q.kod)
            if ok:
                sorunlar.append("Kod hatasız çalışıyor; hata bulma sorusu için hatalı olmalı.")
            else:
                hata_satiri = error_line(err)
                if hata_satiri is not None and str(hata_satiri) != str(q.dogru_cevap).strip():
                    sorunlar.append(
                        f"Python hatayı {hata_satiri}. satırda veriyor, cevap anahtarı {q.dogru_cevap} diyor."
                    )

    q.sorunlar = sorunlar
    q.gecerli = not sorunlar
    return q


def validate_set(qs: QuestionSet) -> QuestionSet:
    for q in qs.sorular:
        validate_question(q)
    return qs
