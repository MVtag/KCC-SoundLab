# KCC SoundLab

Home Assistant based car-audio DSP tuning, measurement and calibration toolkit.

KCC SoundLab is being built around the current KCC car-audio setup with **Goldhorn P2 DSP Pro** as the first supported DSP. The long-term goal is a guided tuning environment for channel setup, crossover, time alignment, measurement, EQ, presets and eventually controlled DSP write-back.

> **v0.6 is a tuning, crossover, measurement and EQ assistant.** It stores tuning data inside the integration, but it does not yet write settings directly to the Goldhorn DSP.

## v0.6 features

- Configure a Goldhorn P2 DSP Pro workspace from the Home Assistant UI.
- Model 1–12 active outputs while keeping Home Assistant clean with only two status entities.
- Edit channel name, speaker, role and physical location directly in SoundLab.
- Store gain, phase, polarity, HPF and LPF settings in the internal workspace.
- Automatically calculate physical time-alignment delay from the furthest speaker.
- Add HolmImpulse fine correction per channel and track polarity/alignment verification.
- Save up to 20 complete tuning snapshots.
- **Measurement Center** with up to 20 persistent HolmImpulse measurement sessions.
- **Crossover Lab** for two-output electrical handoff setup and comparison.
- **EQ / Target Curve** workspace with 31 EQ bands per output.
- Each EQ band stores enabled state, frequency, gain and Q.
- Electrical EQ preview on a logarithmic frequency graph.
- Global target curve overlay with Flat, KCC SQ Draft, Warm and Custom modes.
- Six editable target-curve gain anchors from 20 Hz to 20 kHz.
- Copy all EQ bands from one output to another.
- Reset one output back to a flat 31-band EQ.
- EQ and target curve are included in tuning snapshots.
- Compact status entity exposes active EQ-band count and current target curve without adding new parameter entities.
- Open SoundLab directly from the Home Assistant sidebar.

## Workspaces

- **Overview** – system summary, channel map, presets and final delay overview.
- **Channels** – channel setup, gain/phase/polarity and per-channel filter controls.
- **Time Alignment** – physical distance, HolmImpulse fine correction, verification and final delay.
- **Crossover** – paired-output filter comparison, handoff analysis and direct HPF/LPF editing.
- **EQ** – 31-band channel EQ, electrical preview, copy/reset tools and target curve.
- **Measurement** – HolmImpulse sessions, channel-by-channel results and arrival comparison.
- **Presets** – save, restore and delete complete tuning snapshots including EQ/target data.

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

The internal workspace remains backward compatible with existing channel/tuning and measurement data. When upgrading to v0.6, each existing output receives a flat default 31-band EQ and the target curve defaults to Flat. Existing gain, crossover, phase, time-alignment, measurement and snapshot data remain intact.

No new Home Assistant parameter entities are created.

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

## Crossover Lab

Select any two active outputs. SoundLab orders them as a low-frequency and high-frequency side based on their roles and compares:

`low-side LPF ↔ high-side HPF`

The handoff is classified as **Matched**, **Gap** or **Overlap** using the electrical crossover frequencies. SoundLab also shows octave offset plus whether filter type and slope match.

The plotted curves are setup sketches based on filter frequency and nominal dB/oct slope. They are not acoustic predictions. Final crossover decisions must be verified from the measured summed response and phase after installation.

## EQ / Target Curve

The P2 DSP Pro workspace uses 31 EQ bands per output. SoundLab stores the following values for each band:

- enabled / disabled,
- frequency from 20 Hz to 20 kHz,
- gain from -12 dB to +12 dB,
- Q from 0.1 to 20.

The EQ graph is an **electrical preview** used for workspace planning. It is not a substitute for an acoustic measurement.

The target curve is a separate reference overlay. The built-in **KCC SQ Draft** and **Warm** curves are starting references only; they do not automatically apply EQ. Editing any target point changes the target mode to Custom.

A complete tuning snapshot stores the channel EQ and the active target curve alongside crossover, gain, phase and time alignment.

## Measurement Center

Create one session per microphone/listening position and keep the same HolmImpulse timing/reference arrangement across all channels in that session. SoundLab can then compare impulse arrival times consistently.

`relative_delay_ms = latest_impulse_ms - channel_impulse_ms`

This is measurement evidence, not automatic DSP write-back. Final tuning changes remain deliberate and are entered through the relevant SoundLab workspace.

## Frontend architecture

The SoundLab UI is bundled with the integration and registered as a Home Assistant custom sidebar panel. The panel reads and writes the persistent tuning/measurement workspace through a small KCC SoundLab WebSocket API instead of creating a Home Assistant entity for every DSP parameter.

Frontend module imports are versioned with the integration version. CI validates JavaScript syntax and verifies that local module cache keys exactly match `manifest.json` to prevent stale mixed-version frontend modules.

## Planned next steps

- Subwoofer phase/alignment workflow with guided comparisons.
- Measurement-aware EQ suggestions after real measurement data is available.
- Import/compare measurement files and tuning sessions.
- Configurable car/channel-map positions beyond the first five-channel profile.
- Research direct Goldhorn controller/protocol support and write-back.