"""Claude API'si sahte (mock) bir istemciyle test edilir; API anahtarı gerekmez."""

from types import SimpleNamespace

from soru_uretici.generator import TOOL_NAME, QuestionGenerator

IYI = {
    "tur": "kod_ciktisi", "soru": "Çıktı?", "kod": "print(1 + 1)",
    "secenekler": ["2", "11", "1", "0"], "dogru_cevap": "2", "aciklama": "1+1=2", "zorluk": "kolay",
}
KOTU = {**IYI, "dogru_cevap": "11"}  # Kod 2 yazar, cevap anahtarı yanlış


class FakeClient:
    """Sırayla verilen cevapları döndüren sahte Anthropic istemcisi."""

    def __init__(self, yanitlar):
        self.yanitlar = list(yanitlar)
        self.cagrilar = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.cagrilar.append(kwargs)
        sorular = self.yanitlar.pop(0)
        blok = SimpleNamespace(type="tool_use", name=TOOL_NAME, input={"sorular": sorular})
        return SimpleNamespace(content=[blok])


def test_arac_zorunlu_kullaniliyor():
    client = FakeClient([[IYI]])
    QuestionGenerator(client=client, model="test").generate("toplama", adet=1)
    cagri = client.cagrilar[0]
    assert cagri["tool_choice"] == {"type": "tool", "name": TOOL_NAME}
    assert cagri["tools"][0]["name"] == TOOL_NAME


def test_hatali_soru_claudea_geri_gonderilip_duzeltilir():
    client = FakeClient([[IYI, KOTU], [IYI]])
    qs = QuestionGenerator(client=client, model="test").generate("toplama", adet=2)
    assert len(client.cagrilar) == 2
    assert "Gerçek çıktı" in client.cagrilar[1]["messages"][0]["content"]
    assert qs.gecerli_sayisi == 2 and qs.onarim_turu == 1


def test_duzelmezse_uyari_ile_birakilir():
    client = FakeClient([[KOTU], [KOTU], [KOTU]])
    qs = QuestionGenerator(client=client, model="test", max_onarim=2).generate("toplama", adet=1)
    assert len(client.cagrilar) == 3
    assert qs.gecerli_sayisi == 0 and qs.sorular[0].sorunlar
