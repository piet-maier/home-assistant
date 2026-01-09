import typing

import voluptuous
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ENTITIES, CONF_NAME, Platform
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
)

from .const import DOMAIN, SENSOR


class ThermostatConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, typing.Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=voluptuous.Schema(
                {
                    voluptuous.Required(CONF_NAME): str,
                    voluptuous.Required(CONF_ENTITIES): EntitySelector(
                        EntitySelectorConfig(
                            domain=Platform.CLIMATE, multiple=True, reorder=True
                        )
                    ),
                    SENSOR: EntitySelector(
                        EntitySelectorConfig(domain=Platform.SENSOR)
                    ),
                }
            ),
        )
