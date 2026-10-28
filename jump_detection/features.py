"""Normalize goruntu koordinatlarindan govde ozelligini hesapla."""


def govde_y_hesapla(noktalar):
    """Omuz ve kalca merkezlerinin ortalama Y koordinatini dondur."""
    # Omuz ve kalca merkezlerinin ortalama yuksekligi
    omuz_y = (noktalar[11].y + noktalar[12].y) / 2
    kalca_y = (noktalar[23].y + noktalar[24].y) / 2
    govde_y = (omuz_y + kalca_y) / 2
    return govde_y
