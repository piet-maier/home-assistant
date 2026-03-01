import typing

import voluptuous
from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN

SCHEMA = voluptuous.Schema({voluptuous.Required("street"): int})


class AbfallConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, typing.Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="Abfall", data=user_input)

        return self.async_show_form(step_id="user", data_schema=SCHEMA)

    async def async_step_reconfigure(
        self, user_input: dict[str, typing.Any] | None = None
    ):
        if user_input is not None:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(), data_updates=user_input
            )

        return self.async_show_form(step_id="reconfigure", data_schema=SCHEMA)
