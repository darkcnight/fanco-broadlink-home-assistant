"""Learn RF codes from a Fanco (or any 433 MHz) remote with a Broadlink RM4 Pro, at a FIXED frequency.

Why: Home Assistant's `remote.learn_command` (command_type: rf) first runs a frequency sweep, and on the
RM4 Pro / RM4C Pro that sweep often fails with "No radiofrequency found". Telling the Broadlink to listen
on 433.92 MHz directly skips the sweep and works.

Usage (needs https://docs.astral.sh/uv/ or `pip install broadlink`):

  uvx --with broadlink python fanco_learn.py --host 192.168.1.50 --buttons light,off,1,2,3,4,5,6
  uvx --with broadlink python fanco_learn.py --host 192.168.1.50 --buttons light --presses 1

For every button it asks for N separate taps (default 4) and captures each one. Several captures per
button matter for remotes that send a changing sequence byte (see README). Results are printed as
`b64:...` strings (ready for Home Assistant's remote.send_command) and saved to a JSON file.
"""
import argparse, base64, json, pathlib, time

import broadlink
from broadlink.exceptions import ReadError, StorageError

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--host", required=True, help="Broadlink IP address")
ap.add_argument("--freq", type=float, default=433.92, help="frequency in MHz (default 433.92)")
ap.add_argument("--buttons", default="light,off,1,2,3,4,5,6", help="comma-separated button names, in the order you will press them")
ap.add_argument("--presses", type=int, default=4, help="captures per button (default 4)")
ap.add_argument("--timeout", type=int, default=20, help="seconds to wait for each press (default 20)")
ap.add_argument("--out", default="fanco_codes.json", help="output JSON file (default fanco_codes.json)")
args = ap.parse_args()

dev = broadlink.hello(args.host)
dev.auth()
print(f"Connected to {dev.model or dev.type} at {args.host}. Listening on {args.freq} MHz.")
print("Hold the remote close to the Broadlink. Tap once per prompt; do not hold the button.")


def capture():
    dev.find_rf_packet(args.freq)
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        time.sleep(0.5)
        try:
            return base64.b64encode(dev.check_data()).decode()
        except (ReadError, StorageError):
            continue
    return None


out = pathlib.Path(args.out)
codes = {}
try:
    for button in [b.strip() for b in args.buttons.split(",") if b.strip()]:
        codes[button] = []
        print(f"\n=== {button.upper()} ===")
        while len(codes[button]) < args.presses:
            n = len(codes[button]) + 1
            print(f"  [{button} {n}/{args.presses}] tap {button.upper()} once ...", end=" ", flush=True)
            code = capture()
            if code is None:
                print("nothing heard, try again")
                continue
            codes[button].append(code)
            print("got it")
            time.sleep(1.5)  # let the press finish so the next capture is a new press
        out.write_text(json.dumps(codes, indent=1))
finally:
    dev.cancel_sweep_frequency()
    out.write_text(json.dumps(codes, indent=1))

print(f"\nDone. Saved to {out.resolve()}\n")
for button, cs in codes.items():
    for i, c in enumerate(cs, 1):
        print(f"{button}#{i} b64:{c}")
print("\nNext: python fanco_decode.py", out)
