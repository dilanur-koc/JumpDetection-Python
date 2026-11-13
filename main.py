"""Kamera prototipinin geriye uyumlu calistirma noktasi."""


def main(argv=None):
    import argparse

    from game_bridge import DEFAULT_PORT
    from jump_detection.app import main as run

    parser = argparse.ArgumentParser(description="Kamera ile ziplama prototipi")
    parser.add_argument("--game-events", action="store_true", help="Kamera tahminlerini Unity'ye gonder")
    parser.add_argument("--upper-body", action="store_true", help="Bas ve omuzlarla kamera oyun girdisi")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--game-port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    if args.camera_index < 0 or not 1 <= args.game_port <= 65535:
        parser.error("Kamera indeksi negatif olamaz ve oyun portu 1-65535 arasinda olmali")
    if args.upper_body and not args.game_events:
        parser.error("--upper-body icin --game-events gerekli")
    run(camera_index=args.camera_index, game_port=args.game_port if args.game_events else None,
        upper_body=args.upper_body)


if __name__ == "__main__":
    main()
