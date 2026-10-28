"""Mevcut prototip ayarlari; davranis korunarak tasindi."""

MODEL_PATH = "pose_landmarker_lite.task"

# Algoritma ayarlari
KALIBRASYON_SURESI = 3.0
ZIPLAMA_ESIGI = 0.055
HIZ_ESIGI = 0.12
BEKLEME_SURESI = 0.65
DONUS_ESIGI = 0.025

BAGLANTILAR = [
    (11, 12), (11, 13), (13, 15),
    (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27),
    (24, 26), (26, 28)
]
