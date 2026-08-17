"""Config flow for KCC SoundLab."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_CHANNEL_COUNT,
    CONF_DSP_MODEL,
    CONF_VEHICLE,
    DEFAULT_CHANNEL_COUNT,
    DEFAULT_DSP_MODEL,
    DEFAULT_VEHICLE,
    DOMAIN,
    MAX_CHANNELS,
)


class KCCSoundLabConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KCC SoundLab."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        if user_input is not None:
            title = f"{user_input[CONF_VEHICLE]} · {user_input[CONF_DSP_MODEL]}"
            return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_DSP_MODEL, default=DEFAULT_DSP_MODEL): SelectSelector(
                    SelectSelectorConfig(
                        options=[DEFAULT_DSP_MODEL],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_VEHICLE, default=DEFAULT_VEHICLE): TextSelector(),
                vol.Required(
                    CONF_CHANNEL_COUNT, default=DEFAULT_CHANNEL_COUNT
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=MAX_CHANNELS,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
