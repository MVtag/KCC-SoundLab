# KCC SoundLab

Home Assistant based car-audio DSP tuning, measurement and calibration toolkit.

KCC SoundLab is being built around the current KCC car-audio setup with **Goldhorn P2 DSP Pro** as the first supported DSP. The long-term goal is a guided tuning environment for channel setup, crossover, time alignment, measurement, presets and EQ.

> **v0.1 is a tuning assistant.** It stores and calculates tuning values in Home Assistant, but it does not yet write settings directly to the Goldhorn DSP.

## v0.1 features

- Configure a Goldhorn P2 DSP Pro workspace from the Home Assistant UI.
- Model 1–12 active outputs.
- Store per-output distance, gain, phase, polarity, HPF and LPF settings.
- Automatically calculate time-alignment delay from the furthest speaker.
- Expose reference output, path difference and calculated delay as Home Assistant sensors.
- Store a SoundLab preset selection: Driver SQ, Front Both, Bass Mode or Tuning.
- Open **KCC SoundLab directly from the Home Assistant sidebar**.
- Responsive dark SoundLab interface with three initial workspaces:
  - **Overview** – system summary, channel map, presets and delay overview.
  - **Channels** – selected-channel controls and crossover graph.
  - **Time Alignment** – distance table, reference output and guided delay workflow.

## Installation for prototype testing

### HACS custom repository

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/MVtag/KCC-SoundLab` as an **Integration** repository.
3. Download **KCC SoundLab**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration** and search for **KCC SoundLab**.
6. Select **Goldhorn P2 DSP Pro**, enter the vehicle name and choose the number of active outputs.
7. After setup, open **KCC SoundLab** from the Home Assistant sidebar.

### Manual installation

Copy `custom_components/kcc_soundlab` to `/config/custom_components/kcc_soundlab`, restart Home Assistant, and add **KCC SoundLab** from **Settings → Devices & services**.

## Current KCC five-channel profile

The first frontend profile is optimized for the current five-output system:

| Output | Speaker | Role |
|---|---|---|
| OUT A | BLAM FRS2N50 L | Full-range |
| OUT B | BLAM FRS2N50 R | Full-range |
| OUT C | BLAM 165 LSQ L | Midbass |
| OUT D | BLAM 165 LSQ R | Midbass |
| OUT E | BLAM SuperSub12 | Subwoofer |

The backend still supports up to 12 active outputs; configurable speaker names/roles are planned next.

## Time alignment

Enter the physical distance in centimeters for each active output. KCC SoundLab uses the furthest speaker as the **0 ms reference** and calculates the extra delay for every closer speaker.

Formula:

`delay_ms = (furthest_distance_cm - speaker_distance_cm) / 34.3`

The 34.3 cm/ms constant corresponds to approximately 343 m/s speed of sound at 20 °C.

## Frontend architecture

The SoundLab UI is bundled with the integration and registered as a Home Assistant custom sidebar panel. It uses Home Assistant entities and services for live editing and does not require a separate Lovelace resource.

## Planned next steps

- Configurable channel/speaker names and roles.
- Guided HolmImpulse measurement workflow and fine time-alignment offsets.
- Subwoofer phase/alignment workflow.
- Preset snapshots and tuning-session history.
- PEQ and target-curve workflow.
- Import/compare measurement data.
- Research direct Goldhorn controller/protocol support and write-back.
