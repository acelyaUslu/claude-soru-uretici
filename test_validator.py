from soru_uretici.models import Question
from soru_uretici.validator import error_line, run_code, validate_question


def q(**kw):
    base = dict(tur="coktan_secmeli", soru="?", secenekler=["a", "b", "c", "d"], dogru_cevap="a", aciklama="")
    base.update(kw)
    return Question(**base)


def test_run_code_ciktiyi_dondurur():
    ok, out, _ = run_code("print(2 + 3)")
    assert ok and out.strip() == "5"


def test_run_code_zaman_asimi():
    ok, _, err = run_code("while True: pass")
    assert not ok and "Zaman" in err


def test_error_line():
    _, _, err = run_code("a = 1\nb = 2\nprint(c)")
    assert error_line(err) == 3


def test_gecerli_coktan_secmeli():
    assert validate_question(q()).gecerli


def test_dogru_cevap_seceneklerde_degil():
    sonuc = validate_question(q(dogru_cevap="z"))
    assert not sonuc.gecerli and any("seçenekler arasında" in s for s in sonuc.sorunlar)


def test_tekrarlanan_secenek():
    assert not validate_question(q(secenekler=["a", "a", "c", "d"])).gecerli


def test_kod_ciktisi_dogru():
    sonuc = validate_question(
        q(tur="kod_ciktisi", kod="for i in range(3):\n    print(i)", secenekler=["0\n1\n2", "1\n2\n3", "0\n1", "3"],
          dogru_cevap="0\n1\n2")
    )
    assert sonuc.gecerli, sonuc.sorunlar


def test_kod_ciktisi_yanlis_cevap_yakalanir():
    sonuc = validate_question(
        q(tur="kod_ciktisi", kod="print(len('merhaba'))", secenekler=["6", "7", "8", "5"], dogru_cevap="6")
    )
    assert not sonuc.gecerli and "'7'" in sonuc.sorunlar[0]


def test_hata_bulma_dogru_satir():
    sonuc = validate_question(
        q(tur="hata_bulma", kod="x = 5\ny = 'a'\nprint(x + y)", secenekler=["1", "2", "3", "4"], dogru_cevap="3")
    )
    assert sonuc.gecerli, sonuc.sorunlar


def test_hata_bulma_yanlis_satir_yakalanir():
    sonuc = validate_question(
        q(tur="hata_bulma", kod="x = 5\ny = 'a'\nprint(x + y)", secenekler=["1", "2", "3", "4"], dogru_cevap="2")
    )
    assert not sonuc.gecerli


def test_hata_bulma_hatasiz_kod_reddedilir():
    sonuc = validate_question(
        q(tur="hata_bulma", kod="print(1)\nprint(2)", secenekler=["1", "2", "3", "4"], dogru_cevap="1")
    )
    assert not sonuc.gecerli


def test_sistem_islemleri_reddedilir():
    sonuc = validate_question(
        q(tur="kod_ciktisi", kod="import os\nprint(os.getcwd())", secenekler=["a", "b", "c", "d"], dogru_cevap="a")
    )
    assert not sonuc.gecerli
