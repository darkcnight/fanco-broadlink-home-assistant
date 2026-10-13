# Fanco fans + Broadlink + Home Assistant

How to control **Fanco ceiling fans** (433 MHz RF remotes) from **Home Assistant** with a **Broadlink RM4 Pro / RM4C Pro**: speeds, off and the light. No cloud, no extra hardware on the fan.

When we tried this there was almost nothing online about it, and the obvious route fails in two confusing ways:

1. **Home Assistant can't learn the remote.** `remote.learn_command` with `command_type: rf` fails with *"No radiofrequency found within 30 seconds"*, even though the remote is a normal 433.92 MHz remote.
2. **Once learned, the code works once and then stops.** That looks like rolling code. It isn't.

Both have simple fixes, explained below. Tested in Singapore with two different Fanco remotes in October 2026.

## The two findings

### 1. Skip the frequency sweep

Before it listens, HA's RF learning makes the Broadlink sweep for the remote's frequency. On the RM4 Pro that sweep is unreliable and often finds nothing. The Broadlink can be told to listen on **433.92 MHz** directly, which skips the sweep, and then it captures the remote on the first try. HA has no option for that, so [`tools/fanco_learn.py`](tools/fanco_learn.py) does it with the [python-broadlink](https://github.com/mjg59/python-broadlink) library. The codes it prints (`b64:...`) can be sent from HA with `remote.send_command`.

### 2. "Works once, then stops" is not rolling code

We found two kinds of Fanco remote.

**Remote A: buttons 1 to 6, Off, Light (33-bit frames).** Each press sends:

```
[ remote ID, ~17 bits ][ command, 8 bits ][ sequence byte, 8 bits ]
```

- The **remote ID** never changes.
- The **command** identifies the button. On our remote: light `c8`, 1 `d0`, 2 `d2`, 3 `dc`, 4 `ca`, 5 `cf`, 6 `cc`, off `d6`.
- The **last byte changes from press to press** (for example `f2`, `1c`, `7a`, `94` for the light) and repeats after a while.
- The fan **ignores a frame identical to the last one it heard**, so a held button doesn't toggle the light again and again. It accepts any *different* frame.

So replaying one captured code works until the fan hears that exact frame again: from the real remote, or from your own second replay. Real rolling code scrambles most of the message and never repeats this soon, so this isn't that.

**The fix:** capture each button 4 times, then make HA rotate through the captures so it never sends the same frame twice in a row. In our tests, four light captures sent in turn toggled the light four times out of four.

**Remote B: Light, Off, Low, Medium, High (25-bit frames).** A plain fixed code:

```
[ remote ID, 16 bits ][ command, 9 bits ]
```

On our remote: light `000011110`, off `110000000`, low `001100000`, medium `000011000`, high `000000110`. Every press sends the same frame, so a single capture per button works. The fan beeps once, twice or three times to confirm Low, Medium or High.

**Signal details.** Both remotes use pulse-width encoding at 433.92 MHz:
- **Bits:** a short pulse is about 280 µs and a long one about 790 µs. A 1 is a long high then a short low; a 0 is a short high then a long low.
- **Repeats:** each press repeats the frame 4 to 7 times, with gaps of about 8.6 ms (A) or 7.6 ms (B).

(Remote IDs are left out on purpose: anyone in range could control a fan whose ID is published.)

## Quick start

You need a Broadlink RM4 Pro or RM4C Pro already added to Home Assistant (Settings > Devices & services > Broadlink), and [uv](https://docs.astral.sh/uv/) or `pip install broadlink` on a computer that can reach it.

**1. Learn the remote.** Hold the remote close to the Broadlink, run the script with your Broadlink's IP and the buttons your remote has, and tap each button once per prompt:

```bash
uvx --with broadlink python tools/fanco_learn.py --host 192.168.1.50 --buttons light,off,1,2,3,4,5,6
```

**2. See which kind of remote you have:**

```bash
python tools/fanco_decode.py fanco_codes.json
```

It reports whether each button sends a FIXED code or a CHANGING one.

**3. Test from HA.** In Developer tools > Actions, send one code:

```yaml
action: remote.send_command
target:
  entity_id: remote.YOUR_BROADLINK
data:
  command: b64:PASTE_A_CODE
```

To check for the changing-code behaviour: use the real remote a few times, then send the *same* code again. If it's ignored, but a *different* capture of the same button works, you have remote A. Rotate.

**4. Set up Home Assistant.** See [`home-assistant/`](home-assistant):
- [`fanco_rf_send.yaml`](home-assistant/fanco_rf_send.yaml): a script that sends a button and rotates through its captures.
- [`fanco_set_speed.yaml`](home-assistant/fanco_set_speed.yaml): a script that sets a speed and remembers it.
- [`template_helpers.md`](home-assistant/template_helpers.md): a real `fan` entity with speeds, a light button, and dashboard tips.

## Things to know

- **HA can't see the physical remote.** The fan sends nothing back, so after someone uses the remote, HA's speed can be wrong until HA sends the next command. That's why the light is a stateless button rather than an on/off light entity.
- **Occasional miss on remote A.** A command can be ignored if the last press on the real remote happened to use the same capture. Pressing again fixes it.
- **Range.** One Broadlink reached a Fanco fan in another room through walls, but only borderline: 2 of 3 light toggles got through. Sending each speed/off command 3 times fixed it, since repeats only make the fan beep again. The light is a toggle, so it can't be repeated.
- **Fan on a smart wall relay?** Turn the relay on before sending, and wait about 3 s for the fan's receiver to boot. The example script does this.

## Getting the Broadlink onto Wi-Fi without the app

The Broadlink app can **lock** the device so Home Assistant can't control it. [`tools/broadlink_wifi_setup.py`](tools/broadlink_wifi_setup.py) joins it to your Wi-Fi directly instead. It sends the setup to the Broadlink's own address rather than broadcasting it, because on a computer that also has Ethernet the broadcast goes out the wrong interface and never arrives. A Wi-Fi network with no internet access (an IoT VLAN) is fine: the Broadlink works fully locally.

## Contributing

More remotes would make this more useful. If you have a different Fanco remote, or another brand that behaves the same way, please open an issue with:
- a photo of the remote,
- the fan model,
- `fanco_decode.py` output, **with the first 16 to 17 bits (the remote ID) replaced by X**.

Working out the sequence byte's algorithm would let HA generate codes instead of replaying captures. If you crack it, please share.

## License

MIT
