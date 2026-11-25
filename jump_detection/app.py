"""Kamera, MediaPipe ve OpenCV ekran dongusu."""

import time

from .config import BAGLANTILAR, MODEL_PATH
from .detector import reset, update
from .features import govde_y_hesapla
from .game_detector import BodySample, CameraGameDetector, UpperBodySample


def main(*, camera_index=0, game_port=None, upper_body=False):
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

    # OpenCV kamerayı okur ve ekrana çizer; MediaPipe görüntüden vücut noktalarını bulur.
    # Hareket kararını aşağıda CameraGameDetector verir; görüntü doğrudan Unity'ye gitmez.
    landmarker = vision.PoseLandmarker.create_from_options(options)
    kamera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

    if not kamera.isOpened():
        kamera.release()
        landmarker.close()
        raise SystemExit("Kamera acilamadi!")

    durum = reset()
    game_detector = CameraGameDetector(upper_body=upper_body) if game_port is not None else None
    publisher = None
    baslangic = time.monotonic()
    son_zaman_ms = -1

    try:
        if game_detector is not None:
            from game_bridge import GameEventPublisher

            publisher = GameEventPublisher("camera", game_port)
            print("Unity: CAMERA sec, START RUN ve geri sayimi bekle.")
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

            noktalar = sonuc.pose_landmarks[0] if sonuc.pose_landmarks else None
            if noktalar:

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

            if game_detector is not None:
                sample = None
                if noktalar:
                    sample = (UpperBodySample.from_landmarks(noktalar, w / h) if upper_body
                              else BodySample.from_landmarks(noktalar))
                # Karar True olduğunda tek jump_request gönderilir. UDP sayısı,
                # Unity'nin gerçekten zıpladığı anlamına gelmez; oyun ayrıca denetler.
                if game_detector.update(simdi, sample):
                    try:
                        publisher.send_jump()
                    except OSError as exc:
                        raise SystemExit(f"Unity oyun olayi gonderilemedi: {exc}") from exc
                mesaj = game_detector.status
                renk = (0, 255, 0) if mesaj.startswith(("READY", "JUMP", "MOTION")) else (0, 165, 255)
            elif noktalar:
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

            count_label = "UPPER BODY MOTION" if upper_body else "CAMERA JUMPS"
            count_text = (f"{count_label}: {game_detector.count} | UDP SENT: {publisher.sequence}"
                          if game_detector is not None else f"JUMP COUNT: {durum['sayac']}")
            cv2.putText(
                goruntu,
                count_text,
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

            window_title = "Jump Detection - Prototype v1"
            if game_detector is not None:
                window_title = "Camera to Unity - Upper body" if upper_body else "Camera to Unity"
            cv2.imshow(window_title, goruntu)

            tus = cv2.waitKey(1) & 0xFF

            if tus == ord("q"):
                break
            elif tus == ord("r"):
                durum = reset()
                if game_detector is not None:
                    game_detector = CameraGameDetector(upper_body=upper_body)
                print("Kalibrasyon ve sayac sifirlandi!")

    finally:
        if publisher is not None:
            publisher.close()
        kamera.release()
        landmarker.close()
        cv2.destroyAllWindows()
