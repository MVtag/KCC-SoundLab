# KCC SoundLab

Home Assistant based car-audio DSP tuning, measurement and calibration toolkit.

KCC SoundLab is being built around the current KCC car-audio setup with **Goldhorn P2 DSP Pro** as the first supported DSP. The long-term goal is a guided tuning environment for channel setup, crossover, time alignment, measurement, presets and EQ.

> **v0.4 is a tuning and measurement assistant.** It stores tuning and HolmImpulse measurement data inside the integration, but it does not yet write settings directly to the Goldhorn DSP.

## v0.4 features

- Configure a Goldhorn P2 DSP Pro workspace from the Home Assistant UI.
- Model 1–12 active outputs while keeping Home Assistant clean with only two status entities.
- Edit channel name, speaker, role and physical location directly in SoundLab.
- Store gain, phase, polarity, HPF and LPF settings in the internal workspace.
- Automatically calculate physical time-alignment delay from the furthest speaker.
- Add HolmImpulse fine correction per channel and track polarity/alignment verification.
- Save up to 20 complete tuning snapshots.
- **Measurement Center** with up to 20 persistent HolmImpulse measurement sessions.
- Store listening position, setup notes and per-channel measurement data:
  - impulse peak time in ms,
  - level in dB,
  - observed polarity,
  - channel notes,
  - measured/completed state.
- Compare relative arrival time inside a measurement session using `latest impulse - channel impulse`.
- Keep measurement evidence separate from tuning changes; v0.4 does not automatically overwrite DSP delay values from measurement data.
- Open SoundLab directly from the Home Assistant sidebar.

## Workspaces

- **Overview** – system summary, channel map, presets and final delay overview.
- **Channels** – channel setup, gain/phase/polarity, crossover controls and graph.
- **Time Alignment** – physical distance, HolmImpulse fine correction, verification and final delay.
- **Measurement** – HolmImpulse sessions, channel-by-channel results and arrival comparison.
- **Presets** – save, restore and delete complete tuning snapshots.

## Installation for prototype testing

### HACS custom repository

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/MVtag/KCC-SoundLab` as an **Integration** repository.
3. Download **KCC SoundLab**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration** and search for **KCC SoundLab**.
6. Select **Goldhorn P2 DSP Pro**, enter the vehicle name and choose the number of active outputs.
7. Open **KCC SoundLab** from the Home Assistant sidebar.

### Updating from earlier versions

The internal workspace remains backward compatible with existing channel/tuning data. Measurement-session storage is added alongside the existing tuning snapshots; no new Home Assistant parameter entities are created.

## Current KCC five-channel profile

| Output | Speaker | Role | Default location |
|---|---|---|---|
| OUT A | BLAM FRS2N50 L | Full-range | Front left dash |
| OUT B | BLAM FRS2N50 R | Full-range | Front right dash |
| OUT C | BLAM 165 LSQ L | Midbass | Front left door |
| OUT D | BLAM 165 LSQ R | Midbass | Front right door |
| OUT E | BLAM SuperSub12 | Subwoofer | Boot / trunk |

All channel names, speakers, roles and locations are editable from the Channels workspace. The backend supports up to 12 active outputs.

## Time alignment

`physical_delay_ms = (furthest_distance_cm - speaker_distance_cm) / 34.3`

`recommended_delay_ms = physical_delay_ms + fine_delay_ms`

The recommended delay is clamped to 0–20 ms. Positive fine correction adds delay; negative correction removes delay down to 0 ms.

## Measurement Center

Create one session per microphone/listening position and keep the same HolmImpulse timing/reference arrangement across all channels in that session. SoundLab can then compare impulse arrival times consistently.

`relative_delay_ms = latest_impulse_ms - channel_impulse_ms`

This is measurement evidence, not automatic DSP write-back. Final tuning changes remain deliberate and are entered through Time Alignment.

## Frontend architecture

The SoundLab UI is bundled with the integration and registered as a Home Assistant custom sidebar panel. The panel reads and writes the persistent tuning/measurement workspace through a small KCC SoundLab WebSocket API instead of creating a Home Assistant entity for every DSP parameter.

## Planned next steps

- Crossover Lab with paired-channel overlap visualisation.
- Subwoofer phase/alignment workflow with guided comparisons.
- PEQ and target-curve workflow.
- Import/compare measurement files and tuning sessions.
- Configurable car/channel-map positions beyond the first five-channel profile.
- Research direct Goldhorn controller/protocol support and write-back.
