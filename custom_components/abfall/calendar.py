import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import now

from .coordinator import AbfallCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    coordinator = AbfallCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    async_add_entities([AbfallCalendar(coordinator)])


class AbfallCalendar(CoordinatorEntity[AbfallCoordinator], CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = "RSAG Abfallkalender"
    _attr_unique_id = "rsag-abfallkalender"

    def __init__(self, coordinator: AbfallCoordinator):
        super().__init__(coordinator)

    @property
    def event(self):
        upcoming: list[CalendarEvent] = []

        for item in self.coordinator.data:
            if item.end > now().date():
                upcoming.append(item)

        if upcoming:
            return upcoming[0]

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ):
        result: list[CalendarEvent] = []

        for item in self.coordinator.data:
            if start_date.date() < item.end and end_date.date() >= item.start:
                result.append(item)

        return result
