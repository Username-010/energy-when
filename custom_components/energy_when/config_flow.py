"""Config flow for Energy When."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
    CONF_ALL_IN_SENSOR,
    CONF_APPLIANCE_W,
    CONF_BASE_LOAD_W,
    CONF_DURATION,
    CONF_HOUSE_POWER,
    CONF_PRICE_SENSOR,
    CONF_SOLAR_NOW,
    CONF_SOLAR_REMAINING,
    CONF_SOLAR_TOMORROW,
    CONF_SURCHARGE,
    DEFAULT_APPLIANCE_W,
    DEFAULT_BASE_LOAD_W,
    DEFAULT_DURATION,
    DEFAULT_SURCHARGE,
    DOMAIN,
)

from homeassistant.const import CONF_NAME


def _schema(d: dict[str, Any] | None = None) -> vol.Schema:
    d = d or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=d.get(CONF_NAME, "Was")): TextSelector(),
            vol.Required(CONF_PRICE_SENSOR, default=d.get(CONF_PRICE_SENSOR)): EntitySelector(
                EntitySelectorConfig(domain=["sensor"])
            ),
            vol.Optional(CONF_ALL_IN_SENSOR, default=d.get(CONF_ALL_IN_SENSOR)): EntitySelector(
                EntitySelectorConfig(domain=["sensor"])
            ),
            vol.Optional(
                CONF_SURCHARGE, default=d.get(CONF_SURCHARGE, DEFAULT_SURCHARGE)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0, max=0.5, step=0.01, unit_of_measurement="€/kWh", mode=NumberSelectorMode.BOX
                )
            ),
            vol.Optional(CONF_SOLAR_NOW, default=d.get(CONF_SOLAR_NOW)): EntitySelector(
                EntitySelectorConfig(domain=["sensor"])
            ),
            vol.Optional(CONF_SOLAR_REMAINING, default=d.get(CONF_SOLAR_REMAINING)): EntitySelector(
                EntitySelectorConfig(domain=["sensor"])
            ),
            vol.Optional(CONF_SOLAR_TOMORROW, default=d.get(CONF_SOLAR_TOMORROW)): EntitySelector(
                EntitySelectorConfig(domain=["sensor"])
            ),
            vol.Optional(CONF_HOUSE_POWER, default=d.get(CONF_HOUSE_POWER)): EntitySelector(
                EntitySelectorConfig(domain=["sensor"])
            ),
            vol.Required(
                CONF_DURATION, default=d.get(CONF_DURATION, DEFAULT_DURATION)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0.5, max=12, step=0.5, unit_of_measurement="h", mode=NumberSelectorMode.SLIDER
                )
            ),
            vol.Required(
                CONF_APPLIANCE_W, default=d.get(CONF_APPLIANCE_W, DEFAULT_APPLIANCE_W)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=100, max=11000, step=50, unit_of_measurement="W", mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_BASE_LOAD_W, default=d.get(CONF_BASE_LOAD_W, DEFAULT_BASE_LOAD_W)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0, max=5000, step=50, unit_of_measurement="W", mode=NumberSelectorMode.BOX
                )
            ),
        }
    )


class EnergyWhenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            name = user_input.pop(CONF_NAME)
            await self.async_set_unique_id(f"{DOMAIN}:{name}")
            self._abort_if_unique_id_configured()
            # drop empty optionals
            data = {k: v for k, v in user_input.items() if v not in (None, "")}
            return self.async_create_entry(title=name, data=data)
        return self.async_show_form(step_id="user", data_schema=_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return EnergyWhenOptionsFlow()


class EnergyWhenOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            data = {k: v for k, v in user_input.items() if v not in (None, "")}
            return self.async_create_entry(title="", data=data)
        current = {**self.config_entry.data, **self.config_entry.options}
        current[CONF_NAME] = self.config_entry.title
        return self.async_show_form(step_id="init", data_schema=_schema(current))
