#!/usr/bin/env python3
"""Boot a Spectrle TAP and exercise its menu, grid, sound, and redraws."""

from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

PROMPT = b"command> "
SYMBOL_RE = re.compile(r"^(\S+)\s*=\s*\$([0-9A-Fa-f]+)\b", re.MULTILINE)
ZESARUX_KEY_ENTER = 129
ZX_FRAMES = 23672


def receive_prompt(sock: socket.socket, timeout: float = 3.0) -> str:
    deadline = time.monotonic() + timeout
    response = bytearray()
    while not response.endswith(PROMPT):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(f"ZRCP prompt timeout: {response!r}")
        sock.settimeout(remaining)
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("ZEsarUX closed ZRCP")
        response.extend(chunk)
    return response.decode("latin-1", "replace")


def command(sock: socket.socket, text: str, timeout: float = 3.0) -> str:
    sock.sendall((text + "\n").encode("latin-1"))
    return receive_prompt(sock, timeout)


def send_physical_key(sock: socket.socket, key: int) -> None:
    command(sock, f"send-keys-event {key} 1")
    time.sleep(0.2)
    command(sock, f"send-keys-event {key} 0")


def send_key_until_byte_changes(
    sock: socket.socket,
    key: int,
    address: int,
    previous: int,
    timeout: float,
) -> int:
    """Retry a ZRCP key event if the emulated keyboard misses its first scan."""
    deadline = time.monotonic() + timeout
    last_error: RuntimeError | None = None
    while time.monotonic() < deadline:
        send_physical_key(sock, key)
        remaining = deadline - time.monotonic()
        try:
            return wait_byte_change(sock, address, previous, min(1.0, remaining))
        except RuntimeError as error:
            last_error = error
            time.sleep(0.1)
    raise RuntimeError(f"key {key} was not accepted: {last_error}")


def send_key_until_ocr(
    sock: socket.socket, key: int, needle: str, timeout: float
) -> str:
    deadline = time.monotonic() + timeout
    last_error: RuntimeError | None = None
    while time.monotonic() < deadline:
        send_physical_key(sock, key)
        try:
            return wait_ocr(sock, needle, min(1.0, deadline - time.monotonic()))
        except RuntimeError as error:
            last_error = error
    raise RuntimeError(f"key {key} did not reveal {needle!r}: {last_error}")


def assert_black_border_shadow(sock: socket.socket) -> None:
    bordcr = read_byte(sock, 0x5C48)
    if bordcr & 0x38:
        raise RuntimeError(f"ROM border shadow is not black: ${bordcr:02x}")


def assert_interrupts_alive(sock: socket.socket, stage_name: str) -> None:
    """A sound must not leave interrupts off.

    FRAMES advances only in the ROM's 50 Hz handler, which is also what
    refreshes LAST_K (23560) -- the byte getk() reads.  If it freezes, the
    game will never see another key.
    """
    first = read_byte(sock, ZX_FRAMES)
    time.sleep(0.25)
    if read_byte(sock, ZX_FRAMES) == first:
        raise RuntimeError(
            f"{stage_name}: ROM frame counter froze, so the sound left "
            "interrupts disabled and the keyboard is dead"
        )


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def connect(proc: subprocess.Popen[bytes], port: int, timeout: float) -> socket.socket:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"ZEsarUX exited with status {proc.returncode}")
        try:
            sock = socket.create_connection(("127.0.0.1", port), timeout=0.5)
            receive_prompt(sock)
            return sock
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("could not connect to ZEsarUX")


def read_byte(sock: socket.socket, address: int) -> int:
    response = command(sock, f"read-memory {address} 1")
    for line in response.splitlines():
        if re.fullmatch(r"[0-9A-Fa-f]{2}", line.strip()):
            return int(line.strip(), 16)
    raise RuntimeError(f"cannot read ${address:04x}: {response!r}")


def read_ascii(sock: socket.socket, address: int, length: int) -> str:
    data = bytes(read_byte(sock, address + offset) for offset in range(length))
    try:
        return data.decode("ascii")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"invalid ASCII at ${address:04x}: {data!r}") from error


def cell_pixels(sock: socket.socket, column: int, row: int) -> bytes:
    pixels = bytearray()
    for line in range(8):
        y = row * 8 + line
        address = 0x4000
        address |= (y & 0xC0) << 5
        address |= (y & 0x07) << 8
        address |= (y & 0x38) << 2
        pixels.append(read_byte(sock, address + column))
    return bytes(pixels)


def assert_no_grid_tail(
    sock: socket.socket, selected_length: int, stage_name: str
) -> None:
    grid_left = (33 - selected_length * 4) // 2
    first_column_after_grid = grid_left + selected_length * 4 - 1
    for column in range(first_column_after_grid, 32):
        pixels = cell_pixels(sock, column, 3)
        if any(pixels):
            raise RuntimeError(
                f"{stage_name}: drew content after tile {selected_length} at "
                f"column {column}: pixels {pixels.hex()}"
            )


def wait_byte(sock: socket.socket, address: int, expected: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = read_byte(sock, address)
        if last == expected:
            return
        time.sleep(0.05)
    raise RuntimeError(
        f"${address:04x} did not become ${expected:02x}; last={last!r}"
    )


def wait_byte_change(
    sock: socket.socket, address: int, previous: int, timeout: float
) -> int:
    deadline = time.monotonic() + timeout
    last = previous
    while time.monotonic() < deadline:
        last = read_byte(sock, address)
        if last != previous:
            return last
        time.sleep(0.05)
    raise RuntimeError(f"${address:04x} remained ${last:02x}")


def wait_byte_stable(
    sock: socket.socket, address: int, stable_for: float, timeout: float
) -> int:
    deadline = time.monotonic() + timeout
    last = read_byte(sock, address)
    stable_since = time.monotonic()
    while time.monotonic() < deadline:
        time.sleep(0.05)
        current = read_byte(sock, address)
        if current != last:
            last = current
            stable_since = time.monotonic()
        elif time.monotonic() - stable_since >= stable_for:
            return current
    raise RuntimeError(f"${address:04x} did not stabilize")


def wait_ocr(sock: socket.socket, needle: str, timeout: float) -> str:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        last = command(sock, "get-ocr")
        if needle in last:
            return last
        time.sleep(0.1)
    raise RuntimeError(f"OCR did not contain {needle!r}: {last!r}")


def symbols(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {name: int(value, 16) for name, value in SYMBOL_RE.findall(text)}


def symbol(table: dict[str, int], name: str) -> int:
    for candidate in (name, f"_{name}"):
        if candidate in table:
            return table[candidate]
    raise RuntimeError(f"missing symbol {name}")


def validate_pbm(path: Path) -> None:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and not path.exists():
        time.sleep(0.05)
    data = path.read_bytes()
    if not data.startswith(b"P4\n256 192\n") or len(data) < 6155:
        raise RuntimeError(f"bad screenshot: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine", choices=("48k", "128k"), required=True)
    parser.add_argument("--max-length", type=int, choices=(5, 6), required=True)
    parser.add_argument("--tap", type=Path, required=True)
    parser.add_argument("--map", type=Path, required=True, dest="map_path")
    parser.add_argument("--locale-manifest", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path, required=True)
    parser.add_argument(
        "--zesarux",
        type=Path,
        default=Path("/Applications/ZEsarUX.app/Contents/MacOS/zesarux"),
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    locale = json.loads(args.locale_manifest.read_text(encoding="ascii"))["strings"]
    title = locale["title_48" if args.machine == "48k" else "title_128"]

    table = symbols(args.map_path)
    stage = symbol(table, "zx_boot_stage")
    length = symbol(table, "zx_selected_word_length")
    renders = symbol(table, "zx_render_count")
    redraw_rows = symbol(table, "zx_last_redraw_rows")
    full_renders = symbol(table, "zx_full_render_count")
    last_sound = symbol(table, "zx_last_sound")
    last_submit = symbol(table, "zx_last_submit_result")
    solution_address = symbol(table, "zx_solution")
    markers = (
        stage,
        length,
        renders,
        redraw_rows,
        full_renders,
        last_sound,
        last_submit,
        solution_address + 6,
    )
    if args.machine == "128k" and any(address >= 0xC000 for address in markers):
        raise RuntimeError("smoke markers are not in fixed RAM")

    port = free_port()
    args.screenshot.unlink(missing_ok=True)
    emulator = [
        str(args.zesarux.resolve()),
        "--noconfigfile",
        "--machine",
        args.machine,
        "--tape",
        str(args.tap.resolve()),
        "--vo",
        "null",
        "--ao",
        "null",
        "--nosplash",
        "--enable-remoteprotocol",
        "--remoteprotocol-port",
        str(port),
        "--quickexit",
        "--fastautoload",
    ]
    proc = subprocess.Popen(emulator, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    sock: socket.socket | None = None
    clean = False
    try:
        sock = connect(proc, port, min(args.timeout, 10.0))
        wait_byte(sock, stage, 0x4D, args.timeout)
        wait_ocr(sock, title, 5.0)
        wait_ocr(sock, locale["ascii_notice"], 5.0)
        print(f"PASS {args.machine}: menu and no-accents notice rendered")

        menu_ocr = wait_ocr(sock, locale["mode_5_line"], 5.0)
        if args.max_length == 6:
            wait_ocr(sock, locale["mode_6_line"], 5.0)
        elif locale["mode_6_line"] in menu_ocr:
            raise RuntimeError("5x5-only release exposed the 6x6 menu entry")
        send_physical_key(sock, ord("3"))
        if wait_byte_stable(sock, stage, 0.4, 2.0) != 0x4D:
            raise RuntimeError("key 3 left the 5x5/6x6 menu")
        expected_length = args.max_length
        mode_key = str(expected_length - 4)
        send_key_until_byte_changes(
            sock, ord(mode_key), stage, 0x4D, args.timeout
        )
        wait_byte(sock, stage, 0x47, args.timeout)
        if read_byte(sock, renders) == 0:
            wait_byte_change(sock, renders, 0, args.timeout)
        selected_length = read_byte(sock, length)
        if selected_length != expected_length:
            raise RuntimeError(
                f"{expected_length}x{expected_length} mode selected length "
                f"{selected_length}"
            )
        wait_ocr(sock, locale["type_word"], 5.0)
        assert_no_grid_tail(sock, selected_length, f"{args.machine} initial grid")
        print(f"PASS {args.machine}: selected {expected_length}x{expected_length}")

        previous_full_renders = read_byte(sock, full_renders)
        solution = read_ascii(sock, solution_address, selected_length)
        if not solution.isalpha() or not solution.islower():
            raise RuntimeError(f"invalid smoke solution {solution!r}")

        # Enter on an incomplete row must reject without consuming a try.
        previous_render = read_byte(sock, renders)
        send_key_until_byte_changes(
            sock, ZESARUX_KEY_ENTER, renders, previous_render, args.timeout
        )
        wait_byte_stable(sock, renders, 0.4, args.timeout)
        wait_ocr(sock, locale["not_enough"], 5.0)
        if read_byte(sock, redraw_rows) != 1:
            raise RuntimeError("incomplete word updated more than its message row")
        if read_byte(sock, full_renders) != previous_full_renders:
            raise RuntimeError("incomplete word caused a full-screen redraw")
        if read_byte(sock, last_sound) != 1:
            raise RuntimeError("incomplete word did not select the reject sound")
        assert_black_border_shadow(sock)
        assert_interrupts_alive(sock, f"{args.machine} reject sound")
        assert_no_grid_tail(
            sock, selected_length, f"{args.machine} incomplete submit"
        )
        print(f"PASS {args.machine}: incomplete word rejected without using a try")

        # Typing redraws only the changed tile and the message line.
        for column, letter in enumerate(solution):
            previous_render = read_byte(sock, renders)
            send_key_until_byte_changes(
                sock, ord(letter), renders, previous_render, args.timeout
            )
            if read_byte(sock, redraw_rows) != 2:
                raise RuntimeError("typing did not use a two-row partial update")
            assert_no_grid_tail(
                sock,
                selected_length,
                f"{args.machine} typed column {column}",
            )

        previous_render = read_byte(sock, renders)
        send_key_until_byte_changes(
            sock, ZESARUX_KEY_ENTER, renders, previous_render, args.timeout
        )
        wait_byte(sock, stage, 0x46, args.timeout)
        wait_byte_stable(sock, renders, 0.4, args.timeout)
        wait_ocr(sock, locale["won"], 5.0)
        if read_byte(sock, last_submit) != 3:
            raise RuntimeError("exact solution was not marked as a win")
        if read_byte(sock, last_sound) != 3:
            raise RuntimeError("win did not select the rising sound")
        if read_byte(sock, full_renders) != previous_full_renders:
            raise RuntimeError("submitted word caused a full-screen redraw")
        expected_correct_attr = 0x60
        first_row = 3
        grid_left = (33 - selected_length * 4) // 2
        for column in range(selected_length):
            address = 0x5800 + first_row * 32 + grid_left + column * 4 + 1
            actual = read_byte(sock, address)
            if actual != expected_correct_attr:
                raise RuntimeError(
                    f"tile {column} attribute ${actual:02x}, expected green ${expected_correct_attr:02x}"
                )
        assert_no_grid_tail(sock, selected_length, f"{args.machine} solved grid")
        print(
            f"PASS {args.machine}: no tile drawn after column {selected_length}"
        )
        assert_black_border_shadow(sock)
        assert_interrupts_alive(sock, f"{args.machine} win sound")
        print(
            f"PASS {args.machine}: exact word produced {selected_length} green "
            "tiles and a win"
        )

        command(sock, f"save-screen {args.screenshot.resolve()}")
        validate_pbm(args.screenshot)
        print(f"PASS {args.machine}: screenshot {args.screenshot}")

        sock.sendall(b"exit-emulator\n")
        sock.close()
        sock = None
        proc.wait(timeout=5.0)
        if proc.returncode != 0:
            raise RuntimeError(f"ZEsarUX exit status {proc.returncode}")
        clean = True
        return 0
    finally:
        if sock is not None:
            try:
                sock.sendall(b"exit-emulator\n")
            except OSError:
                pass
            sock.close()
        if not clean and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"smoke: ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
