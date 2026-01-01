import datetime
import logging

from homeassistant.components.calendar import CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client.rsag import RSAG
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AbfallCoordinator(DataUpdateCoordinator[list[CalendarEvent]]):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, client: RSAG):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=datetime.timedelta(weeks=1),
            always_update=False,
        )

        self.client = client

    async def _async_update_data(self):
        if self.config_entry is None:
            raise TypeError("The configuration entry must not be None.")

        return await self.client.async_fetch_data(self.config_entry.data["street"])
