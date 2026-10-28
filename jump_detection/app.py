"""Kamera, MediaPipe ve OpenCV ekran dongusu."""

import time

from .config import BAGLANTILAR, MODEL_PATH
from .detector import reset, update
from .features import govde_y_hesapla


def main():
    if not MODEL_PATH.is_file():
        raise SystemExit(
            f"MediaPipe model dosyasi bulunamadi: {MODEL_PATH}\n"
            "pose_landmarker_lite.task dosyasini proje kokune yerlestirin. "
            "Kurulum ayrintilari icin README.md dosyasina bakin."
        )

    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(MODEL_PATH)),
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
                    govde_y = govde_y_hesapla(noktalar)

                    mesaj, renk, yukselme, hiz = update(durum, simdi, govde_y)

                    if yukselme is not None:
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
