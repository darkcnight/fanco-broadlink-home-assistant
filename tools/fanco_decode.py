"""Decode Broadlink RF captures into bit frames, to see what kind of remote you have.

Usage:
  python fanco_decode.py fanco_codes.json          # JSON from fanco_learn.py
  python fanco_decode.py b64:scC... b64:scC...     # or individual codes

No dependencies. For each capture it prints the most common frame (a capture holds several repeats of
the same frame), as bits and hex, plus how many repeats agreed. Then it tells you whether each button
always sends the same frame (fixed code) or a changing one (sequence byte, see README).

Broadlink RF packet layout: byte 0 = type (0xb1/0xb2 for 433 MHz), byte 1 = repeat count,
bytes 2-3 = payload length (little endian), then pulse lengths in units of ~32.8 us
(one byte each, or 0x00 followed by a 2-byte big-endian value for long gaps).
"""
import base64, collections, json, pathlib, sys

GAP = 60  # pulses longer than this (~2 ms) separate frames


def pulses(code):
    raw = base64.b64decode(code.removeprefix("b64:"))
    n = int.from_bytes(raw[2:4], "little")
    data, out, i = raw[4:4 + n], [], 0
    while i < len(data):
        if data[i] == 0:
            out.append(int.from_bytes(data[i + 1:i + 3], "big"))
            i += 3
        else:
            out.append(data[i])
            i += 1
    return out


def frames(code):
    """Pulse pairs (high, low): long-high + short-low = 1, short-high + long-low = 0."""
    p, result, cur = pulses(code), [], []
    for k in range(0, len(p) - 1, 2):
        hi, lo = p[k], p[k + 1]
        if hi > GAP or lo > GAP:
            if lo > GAP:
                cur.append("1" if hi > 12 else "0")
            result.append("".join(cur))
            cur = []
        else:
            cur.append("1" if hi > lo else "0")
    return [f for f in result if len(f) > 10]


def best(code):
    fs = frames(code)
    if not fs:
        return None, 0, 0
    full = max(len(f) for f in fs)  # a capture can start or end mid-frame; trust complete frames
    frame, count = collections.Counter(f for f in fs if len(f) == full).most_common(1)[0]
    return frame, count, len(fs)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1].endswith(".json"):
        codes = json.loads(pathlib.Path(sys.argv[1]).read_text())
    else:
        codes = {"capture": sys.argv[1:]}
    for button, cs in codes.items():
        print(f"\n{button}")
        seen = set()
        for i, c in enumerate(cs, 1):
            frame, agree, total = best(c)
            if frame is None:
                print(f"  #{i}: no clean frame found")
                continue
            seen.add(frame)
            print(f"  #{i}: {len(frame)} bits  {frame}  0x{int(frame, 2):0{(len(frame) + 3) // 4}x}  ({agree}/{total} repeats agree)")
        if len(cs) > 1 and seen:
            kind = "FIXED code (every press identical)" if len(seen) == 1 else \
                f"CHANGING code ({len(seen)} different frames): rotate through captures, never resend the last one"
            print(f"  -> {kind}")


if __name__ == "__main__":
    main()
