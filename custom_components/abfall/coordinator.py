import datetime
import logging

from homeassistant.components.calendar import CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AbfallCoordinator(DataUpdateCoordinator[list[CalendarEvent]]):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=datetime.timedelta(weeks=1),
            always_update=False,
        )

    async def _async_update_data(self):
        if self.config_entry is None:
            raise TypeError("The configuration entry must not be None.")

        client = async_get_clientsession(self.hass)

        async with client.get(
            "https://www.rsag.de/api/pickup/filter/"
            + str(self.config_entry.data["street"])
            + "/1,2,3,4,6,7/"
            + str(datetime.datetime.now().month)
        ) as response:
            data = await response.json(content_type=None)

            result: list[CalendarEvent] = []

            for item in data[0]["items"]:
                date = datetime.date.fromisoformat(item["pickupdate"])

                result.append(
                    CalendarEvent(
                        date, date + datetime.timedelta(days=1), item["wastetype_name"]
                    )
                )

            return sorted(result, key=lambda item: item.start)
