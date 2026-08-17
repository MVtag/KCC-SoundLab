# KCC SoundLab

Prototype Home Assistant integration for car-audio DSP setup and tuning.

## v0.1 goals

- Create a DSP/vehicle workspace from the Home Assistant UI.
- Model 1-12 active outputs for Goldhorn P2 DSP Pro.
- Store per-output distance, gain, phase, polarity and crossover settings.
- Automatically calculate time-alignment delay from the furthest speaker.
- Expose the calculated reference output, path difference and delay as Home Assistant sensors.

> v0.1 is a tuning assistant. It does **not** yet write settings directly to the Goldhorn DSP.

## Installation for prototype testing

### HACS custom repository

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/MVtag/KCC-SoundLab` as an **Integration** repository.
3. Download **KCC SoundLab**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration** and search for **KCC SoundLab**.
6. Select **Goldhorn P2 DSP Pro**, enter the vehicle name and choose the number of active outputs.

### Manual installation

Copy `custom_components/kcc_soundlab` to `/config/custom_components/kcc_soundlab`, restart Home Assistant, and add **KCC SoundLab** from **Settings → Devices & services**.

## Time alignment

Enter the physical distance in centimeters for each active output. KCC SoundLab uses the furthest speaker as the 0 ms reference and calculates the extra delay for every closer speaker.

Formula:

`delay_ms = (furthest_distance_cm - speaker_distance_cm) / 34.3`

The 34.3 cm/ms constant corresponds to approximately 343 m/s speed of sound at 20 °C.

## Planned next steps

- Rename/output-role editor (FRS L, FRS R, Midbass L, Midbass R, Sub, etc.).
- KCC SoundLab Lovelace card with car overview.
- Guided HolmImpulse time-alignment wizard.
- Presets and tuning-session history.
- PEQ/target curve workflow.
- Research direct Goldhorn control/protocol support.
