import typing

import voluptuous
from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class AbfallConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, typing.Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="Abfall", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=voluptuous.Schema({voluptuous.Required("street"): int}),
        )
