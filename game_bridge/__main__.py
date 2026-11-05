"""Donanimsiz olay gonderimi ve localhost UDP tani alicisi."""

import argparse
import json
import math
import socket
import sys
import time

from . import (DEFAULT_PORT, HOST, MAX_PACKET_BYTES, SOURCE_EVIDENCE,
               GameEventPublisher, GameEventValidator)


def positive_count(text):
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Adet pozitif bir tam sayi olmali") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("Adet pozitif bir tam sayi olmali")
    return value


def finite_seconds(text, allow_zero=False):
    value = float(text)
    if not math.isfinite(value) or value < 0 or (value == 0 and not allow_zero):
        raise argparse.ArgumentTypeError("Sure sonlu ve pozitif olmali")
    return value


def port_number(text, allow_zero=False):
    value = int(text)
    if not (0 if allow_zero else 1) <= value <= 65535:
        raise argparse.ArgumentTypeError("Gecersiz UDP portu")
    return value


def simulate(count=5, interval=1.0, port=DEFAULT_PORT, *, emit=print, sleep=time.sleep):
    # Olaylar gerçek sensör çıktısı değildir; oyun köprüsünü ayrı sınamak içindir.
    with GameEventPublisher("simulator", port) as publisher:
        for index in range(count):
            if index:
                sleep(interval)
            emit(json.dumps(publisher.send_jump()))
    return count


def listen(seconds=10.0, source="simulator", port=DEFAULT_PORT, *, emit=print):
    # Bu tanı alıcısı ve Unity aynı portu aynı anda kullanmamalı.
    validator = GameEventValidator(source)
    accepted = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind((HOST, port))
        print(f"Dinleniyor: {HOST}:{receiver.getsockname()[1]} | kaynak={source}", file=sys.stderr, flush=True)
        deadline = time.monotonic() + seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            # Paket gelmese bile süre sonunda portu bırakır; sürekli beklemez.
            receiver.settimeout(min(0.1, remaining))
            try:
                data, address = receiver.recvfrom(MAX_PACKET_BYTES + 1)
            except socket.timeout:
                continue
            if address[0] != HOST:
                continue
            event = validator.accept(data)
            if event is not None:
                accepted += 1
                emit(json.dumps(event))
    return accepted


def main(argv=None):
    parser = argparse.ArgumentParser(description="Python-oyun localhost olay koprusu")
    commands = parser.add_subparsers(dest="command", required=True)
    sender = commands.add_parser("simulate", help="Donanimsiz sinirli sayida ziplama istegi gonder")
    sender.add_argument("--count", type=positive_count, default=5)
    sender.add_argument("--interval", type=lambda text: finite_seconds(text, True), default=1.0)
    sender.add_argument("--port", type=port_number, default=DEFAULT_PORT)
    receiver = commands.add_parser("listen", help="Unity yerine tani amaciyla olaylari dinle")
    receiver.add_argument("--seconds", type=finite_seconds, default=10.0)
    receiver.add_argument("--source", choices=SOURCE_EVIDENCE, default="simulator")
    receiver.add_argument("--port", type=lambda text: port_number(text, True), default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    try:
        if args.command == "simulate":
            simulate(args.count, args.interval, args.port)
        else:
            count = listen(args.seconds, args.source, args.port)
            print(f"Dinleme bitti. Kabul edilen olay: {count}", file=sys.stderr)
    except OSError as exc:
        print(f"Oyun koprusu hatasi: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOyun koprusu durduruldu.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
