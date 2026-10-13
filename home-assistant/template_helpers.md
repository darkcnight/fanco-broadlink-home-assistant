# Template helpers: a real fan entity and a light button

Create both in **Settings > Devices & services > Helpers > Create helper > Template**. They stay editable in the UI.

## Fan (Template > Fan)

| Field | Value |
|---|---|
| Name | `Ceiling Fan` |
| Speed count | `6` (or `3` for a Low/Medium/High remote) |
| State | `{{ states('input_number.fanco_speed') \| int(0) > 0 }}` |
| Percentage | `{{ ((states('input_number.fanco_speed') \| int(0)) * 100 / 6) \| round(0) }}` |

**Turn on** action:

```yaml
action: script.fanco_set_speed
data:
  speed: "{{ [((percentage | int(0)) * 6 / 100) | round(0) | int, 1] | max if percentage is defined and percentage else 3 }}"
```

**Turn off** action:

```yaml
action: script.fanco_set_speed
data:
  speed: 0
```

**Set percentage** action:

```yaml
action: script.fanco_set_speed
data:
  speed: "{{ ((percentage | int(0)) * 6 / 100) | round(0) | int }}"
```

Replace `6` with `3` everywhere for a 3-speed remote. Use `round`, not `round(0, 'ceil')`: a dashboard
sending 17% for speed 1 would otherwise land on speed 2.

If the fan's power is on a smart relay, add `and is_state('switch.YOUR_FAN_RELAY', 'on')` to the State
template, and an automation that sets `input_number.fanco_speed` to 0 when the relay turns off.

## Light (Template > Button)

The remote's light button is a toggle and the fan reports nothing back, so a tracked on/off state drifts as
soon as someone uses the physical remote. A stateless button is more honest:

| Field | Value |
|---|---|
| Name | `Ceiling Fan Light` |

**Press** action:

```yaml
action: script.fanco_rf_send
data:
  button: light
```

## Dashboard

A slider is a poor fit for a fan with fixed speeds. Speed buttons work better:

- **Tile card** with the `fan-speed` feature, `style: icons`. Good for 3-speed fans.
- **Bubble Card** button with one sub-button per speed, each calling `fan.set_percentage`
  (17, 33, 50, 67, 83, 100 for six speeds). Good for 6-speed fans.

For the light, a button card that calls `button.press`, with the state line hidden.
