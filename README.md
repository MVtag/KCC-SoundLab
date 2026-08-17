# KCC SoundLab

Home Assistant based car-audio DSP tuning, measurement and calibration toolkit.

KCC SoundLab is being built around the current KCC car-audio setup with **Goldhorn P2 DSP Pro** as the first supported DSP. The long-term goal is a guided tuning environment for channel setup, crossover, time alignment, measurement, presets and EQ.

> **v0.3 is a tuning assistant.** It stores, calculates and snapshots tuning values inside the integration, but it does not yet write settings directly to the Goldhorn DSP.

## v0.3 features

- Configure a Goldhorn P2 DSP Pro workspace from the Home Assistant UI.
- Model 1–12 active outputs.
- Keep Home Assistant clean with only two useful status entities.
- Edit channel name, speaker, role and physical location directly in SoundLab.
- Store gain, phase, polarity, HPF and LPF settings in the internal SoundLab workspace.
- Automatically calculate physical time-alignment delay from the furthest speaker.
- Add a **HolmImpulse fine correction** per channel; positive values add delay to the physical calculation.
- Track polarity verification and alignment verification per channel.
- Guide the tuning through Measure → Polarity → Time Alignment → Sub Alignment → Save Preset.
- Save up to 20 complete tuning snapshots and restore them later.
- Open **KCC SoundLab directly from the Home Assistant sidebar**.
- Responsive dark SoundLab interface with four workspaces:
  - **Overview** – system summary, channel map, presets and final delay overview.
  - **Channels** – channel setup, gain/phase/polarity, crossover controls and graph.
  - **Time Alignment** – distance, HolmImpulse fine correction, verification and final delay.
  - **Presets** – save, restore and delete complete tuning snapshots.

## Installation for prototype testing

### HACS custom repository

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/MVtag/KCC-SoundLab` as an **Integration** repository.
3. Download **KCC SoundLab**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration** and search for **KCC SoundLab**.
6. Select **Goldhorn P2 DSP Pro**, enter the vehicle name and choose the number of active outputs.
7. After setup, open **KCC SoundLab** from the Home Assistant sidebar.

### Updating from v0.1/v0.2

The internal workspace is backward compatible with the saved v0.2 channel data. New v0.3 channel-profile and verification fields receive defaults automatically. Existing tuning values remain in the integration storage.

### Manual installation

Copy `custom_components/kcc_soundlab` to `/config/custom_components/kcc_soundlab`, restart Home Assistant, and add **KCC SoundLab** from **Settings → Devices & services**.

## Current KCC five-channel profile

| Output | Speaker | Role | Default location |
|---|---|---|---|
| OUT A | BLAM FRS2N50 L | Full-range | Front left dash |
| OUT B | BLAM FRS2N50 R | Full-range | Front right dash |
| OUT C | BLAM 165 LSQ L | Midbass | Front left door |
| OUT D | BLAM 165 LSQ R | Midbass | Front right door |
| OUT E | BLAM SuperSub12 | Subwoofer | Boot / trunk |

All channel names, speakers, roles and locations are editable from the Channels workspace. The backend still supports up to 12 active outputs.

## Time alignment

Enter the physical distance in centimeters for each active output. KCC SoundLab uses the furthest speaker as the **0 ms reference** and calculates the extra delay for every closer speaker.

`physical_delay_ms = (furthest_distance_cm - speaker_distance_cm) / 34.3`

The 34.3 cm/ms constant corresponds to approximately 343 m/s speed of sound at 20 °C.

v0.3 then allows a HolmImpulse fine correction:

`recommended_delay_ms = physical_delay_ms + fine_delay_ms`

The recommended delay is clamped to the current Goldhorn P2 DSP Pro delay range of 0–20 ms. A positive fine correction adds delay; a negative correction removes delay down to 0 ms.

## Frontend architecture

The SoundLab UI is bundled with the integration and registered as a Home Assistant custom sidebar panel. The panel reads and writes the persistent tuning workspace through a small KCC SoundLab WebSocket API instead of creating a Home Assistant entity for every DSP parameter.

## Planned next steps

- Dedicated Measurement Center for HolmImpulse measurement sessions.
- Subwoofer phase/alignment workflow with guided comparisons.
- PEQ and target-curve workflow.
- Import/compare measurement data and tuning sessions.
- Configurable car/channel-map positions beyond the first five-channel profile.
- Research direct Goldhorn controller/protocol support and write-back.
