"""Constants for KCC SoundLab."""

DOMAIN = "kcc_soundlab"
NAME = "KCC SoundLab"
VERSION = "0.6.12"

CONF_DSP_MODEL = "dsp_model"
CONF_VEHICLE = "vehicle"
CONF_CHANNEL_COUNT = "channel_count"

DEFAULT_DSP_MODEL = "Goldhorn P2 DSP Pro"
DEFAULT_VEHICLE = "Car"
DEFAULT_CHANNEL_COUNT = 5
MAX_CHANNELS = 12

PLATFORMS = ["sensor"]

# Approximate speed of sound at 20 C: 343 m/s = 34.3 cm/ms.
CM_PER_MS = 34.3