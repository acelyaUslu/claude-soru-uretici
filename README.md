# 🧩 Claude ile Python Soru Üretici

Çocuklara ve gençlere (9–18 yaş) Python öğreten eğitmenler için, **seviyeye uygun ve otomatik doğrulanmış** soru setleri üreten bir araç.
Soruları Claude üretir. Kod içeren her soru gerçekten **çalıştırılarak** kontrol edilir, hatalı çıkan sorular da Claude'a geri gönderilip düzelttirilir.

> Neden? LLM'ler soru üretirken sık sık yanlış cevap anahtarı yazar (ör. `range(1, 4)` toplamını 10 sanmak).
> Bu proje, üretilen içeriğe körü körüne güvenmek yerine **üret → doğrula → düzelttir** döngüsü kurar.

![Uygulama ekranı](docs/ekran.png)

## Özellikler

- **3 soru türü:** kavram (çoktan seçmeli), kod çıktısı tahmini, hatalı satırı bulma
- **3 seviye:** Başlangıç (9–12), Orta (13–15), İleri (16–18)
- **Yapılandırılmış çıktı:** Claude cevabı serbest metin olarak değil, JSON şemalı bir araç (tool use) üzerinden döndürür
- **Otomatik doğrulama:**
  - 4 benzersiz seçenek var mı, doğru cevap seçenekler arasında mı?
  - *Kod çıktısı* sorularında kod çalıştırılır, gerçek çıktı cevap anahtarıyla karşılaştırılır
  - *Hata bulma* sorularında kodun gerçekten hata verdiği ve hatanın **cevap anahtarındaki satırda** oluştuğu kontrol edilir
- **Kendini düzelten döngü:** Doğrulamayı geçemeyen sorular, bulunan sorunlarla birlikte Claude'a geri gönderilir (en fazla 2 tur)
- **Dışa aktarma:** öğrenci sayfası (.md), cevap anahtarlı sayfa (.md), JSON
- **Demo modu:** API anahtarı olmadan örnek soru setiyle çalışır

## Mimari

```
Eğitmen (Streamlit) ──► QuestionGenerator ──► Claude API (tool_choice: soru_setini_kaydet)
                              │                         │
                              │◄──── JSON soru seti ────┘
                              ▼
                         validator.py ── kodu ayrı Python sürecinde çalıştırır
                              │
                 hatalı soru varsa ──► sorunlarla birlikte Claude'a geri gönder (onarım)
                              ▼
                     export.py ──► öğrenci sayfası / cevap anahtarı / JSON
```

| Dosya | Görev |
|---|---|
| `soru_uretici/generator.py` | Prompt, araç şeması, Claude çağrısı ve onarım döngüsü |
| `soru_uretici/validator.py` | Yapısal kontroller, kodu çalıştırma, hata satırı tespiti |
| `soru_uretici/export.py` | Markdown ve JSON çıktıları |
| `app.py` | Streamlit arayüzü |
| `tests/` | Doğrulayıcı testleri ve sahte istemciyle Claude akışı testleri |

## Kurulum

```bash
git clone https://github.com/acelyaUslu/claude-soru-uretici.git
cd claude-soru-uretici
pip install -r requirements.txt

cp .env.example .env        # ANTHROPIC_API_KEY değerini yaz
export $(cat .env | xargs)  # Windows'ta: set ANTHROPIC_API_KEY=...

streamlit run app.py
```

API anahtarı vermezsen uygulama `examples/ornek_soru_seti.json` içindeki örnek setle açılır.

### Kod içinden kullanım

```python
from soru_uretici import QuestionGenerator
from soru_uretici.export import to_markdown

gen = QuestionGenerator()  # ANTHROPIC_API_KEY ortam değişkenini kullanır
qs = gen.generate(konu="listeler", seviye="orta", turler=["kod_ciktisi", "hata_bulma"], adet=6)

print(f"{qs.gecerli_sayisi}/{len(qs.sorular)} soru doğrulandı")
open("listeler.md", "w", encoding="utf-8").write(to_markdown(qs))
```

## Testler

```bash
python -m pytest -q
```

Claude çağrıları testlerde sahte (mock) istemciyle simüle edilir; API anahtarı gerekmez.

## Güvenlik notu

Üretilen kodlar zaman aşımı olan ayrı bir Python sürecinde, boş bir geçici klasörde ve izole modda çalıştırılır; sistemle etkileşen ifadeler (`import os`, `open(` vb.) reddedilir.
Bu yaklaşım bir demo için yeterlidir ama tam bir sandbox değildir. Gerçek kullanımda doğrulama adımı bir konteyner içinde çalıştırılmalıdır.

## Yol haritası

- [ ] PDF çıktı
- [ ] Öğrencinin yanlış yaptığı konulara göre kişiselleştirilmiş tekrar seti
- [ ] Soru bankası ve tekrar eden soruların tespiti

---

Geliştiren: **Açelya Uslu** · Bilgisayar Mühendisliği Yüksek Lisans, Manisa Celal Bayar Üniversitesi
