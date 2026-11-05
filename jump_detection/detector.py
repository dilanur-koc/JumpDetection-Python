"""Kamera prototipinin mevcut kalibrasyon ve ziplama kurallari."""

from collections import deque
from statistics import median

from .config import (
    KALIBRASYON_SURESI,
    ZIPLAMA_ESIGI,
    HIZ_ESIGI,
    BEKLEME_SURESI,
    DONUS_ESIGI,
)


def reset():
    return {
        "kalibrasyon": [],
        "referans": None,
        "gecmis": deque(maxlen=5),
        "sayac": 0,
        "hazir": True,
        "son_ziplama": -100.0
    }


def update(durum, simdi, govde_y):
    """Gecerli bir govde olcumunu isle; mesaj, renk, yukselme ve hizi dondur.

    Kalibrasyon sirasinda yukselme ve hiz None olur. Takip kaybinda cagiran
    uygulama mevcut davranis geregi yalnizca gecmis tamponunu temizler.
    """
    yukselme = None
    hiz = None
    durum["gecmis"].append((simdi, govde_y))

    if durum["referans"] is None:
        durum["kalibrasyon"].append((simdi, govde_y))

        # Son 3 saniyedeki ornekler
        durum["kalibrasyon"] = [
            p for p in durum["kalibrasyon"]
            if simdi - p[0] <= KALIBRASYON_SURESI
        ]

        if (len(durum["kalibrasyon"]) >= 10 and
            durum["kalibrasyon"][-1][0] -
            durum["kalibrasyon"][0][0] >=
            KALIBRASYON_SURESI - 0.1):

            degerler = [
                p[1] for p in durum["kalibrasyon"]
            ]
            durum["referans"] = median(degerler)
            mesaj = "READY - JUMP!"
        else:
            mesaj = "CALIBRATING - STAND STILL"

        renk = (0, 255, 255)

    else:
        # MediaPipe'da kucuk Y = goruntude daha yukari
        yukselme = durum["referans"] - govde_y

        hiz = 0.0
        if len(durum["gecmis"]) >= 2:
            eski_t, eski_y = durum["gecmis"][0]
            dt = simdi - eski_t

            if dt > 0:
                hiz = (eski_y - govde_y) / dt

        if (
            durum["hazir"]
            and yukselme > ZIPLAMA_ESIGI
            and hiz > HIZ_ESIGI
            and simdi - durum["son_ziplama"] >
            BEKLEME_SURESI
        ):
            durum["sayac"] += 1
            durum["son_ziplama"] = simdi
            durum["hazir"] = False

            print(
                f"JUMP DETECTED! "
                f"Toplam: {durum['sayac']}"
            )

        # Oyuncu tekrar baslangic yuksekligine donunce
        if (
            not durum["hazir"]
            and abs(yukselme) < DONUS_ESIGI
            and simdi - durum["son_ziplama"] >
            BEKLEME_SURESI
        ):
            durum["hazir"] = True

        if simdi - durum["son_ziplama"] < 0.5:
            mesaj = "JUMP DETECTED!"
            renk = (0, 255, 0)
        elif durum["hazir"]:
            mesaj = "READY - JUMP!"
            renk = (255, 255, 0)
        else:
            mesaj = "WAIT FOR LANDING"
            renk = (0, 165, 255)

    return mesaj, renk, yukselme, hiz
