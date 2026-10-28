import cv2
import mediapipe as mp
import time
from collections import deque
from statistics import median

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

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

def reset():
    return {
        "kalibrasyon": [],
        "referans": None,
        "gecmis": deque(maxlen=5),
        "sayac": 0,
        "hazir": True,
        "son_ziplama": -100.0
    }


def main():
    options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1
    )

    landmarker = vision.PoseLandmarker.create_from_options(options)
    kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not kamera.isOpened():
        landmarker.close()
        raise SystemExit("Kamera acilamadi!")

    durum = reset()
    baslangic = time.monotonic()
    son_zaman_ms = -1

    try:
        while True:
            basarili, goruntu = kamera.read()

            if not basarili:
                print("Goruntu alinamadi!")
                break

            goruntu = cv2.flip(goruntu, 1)
            h, w = goruntu.shape[:2]
            simdi = time.monotonic()

            rgb = cv2.cvtColor(goruntu, cv2.COLOR_BGR2RGB)
            mp_goruntu = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb
            )

            zaman_ms = int((simdi - baslangic) * 1000)
            zaman_ms = max(zaman_ms, son_zaman_ms + 1)
            son_zaman_ms = zaman_ms

            sonuc = landmarker.detect_for_video(
                mp_goruntu, zaman_ms
            )

            mesaj = "BODY NOT DETECTED"
            renk = (0, 0, 255)

            if sonuc.pose_landmarks:
                noktalar = sonuc.pose_landmarks[0]

                for a, b in BAGLANTILAR:
                    p1, p2 = noktalar[a], noktalar[b]

                    if p1.visibility > 0.5 and p2.visibility > 0.5:
                        cv2.line(
                            goruntu,
                            (int(p1.x * w), int(p1.y * h)),
                            (int(p2.x * w), int(p2.y * h)),
                            (0, 255, 0), 2
                        )

                for p in noktalar:
                    if p.visibility > 0.5:
                        cv2.circle(
                            goruntu,
                            (int(p.x * w), int(p.y * h)),
                            4, (0, 0, 255), -1
                        )

                gerekli = [11, 12, 23, 24]

                if all(noktalar[i].visibility > 0.6 for i in gerekli):
                    # Omuz ve kalca merkezlerinin ortalama yuksekligi
                    omuz_y = (noktalar[11].y + noktalar[12].y) / 2
                    kalca_y = (noktalar[23].y + noktalar[24].y) / 2
                    govde_y = (omuz_y + kalca_y) / 2

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

                        cv2.putText(
                            goruntu,
                            f"Rise: {yukselme:.3f} Speed: {hiz:.3f}",
                            (20, 110),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, (255, 255, 255), 2
                        )

                else:
                    mesaj = "SHOW SHOULDERS AND HIPS"
                    renk = (0, 165, 255)
                    durum["gecmis"].clear()

            else:
                durum["gecmis"].clear()

            cv2.putText(
                goruntu, mesaj, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, renk, 2
            )

            cv2.putText(
                goruntu,
                f"JUMP COUNT: {durum['sayac']}",
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.85, (255, 255, 255), 2
            )

            cv2.putText(
                goruntu, "R: Reset | Q: Quit",
                (20, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (255, 255, 255), 1
            )

            cv2.imshow("Jump Detection - Prototype v1", goruntu)

            tus = cv2.waitKey(1) & 0xFF

            if tus == ord("q"):
                break
            elif tus == ord("r"):
                durum = reset()
                print("Kalibrasyon ve sayac sifirlandi!")

    finally:
        kamera.release()
        landmarker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
