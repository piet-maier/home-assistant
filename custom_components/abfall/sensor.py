import itertools

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import now

from .const import DOMAIN
from .coordinator import AbfallCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([AbfallSensor(coordinator)])


class AbfallSensor(CoordinatorEntity[AbfallCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "RSAG Abfuhrtermin"
    _attr_unique_id = "rsag-abfuhrtermin"

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: AbfallCoordinator):
        super().__init__(coordinator)

    @property
    def native_value(self):
        for item in self.coordinator.data:
            if item.start >= now().date():
                return item.start

    @property
    def extra_state_attributes(self):
        for date, iterator in itertools.groupby(
            self.coordinator.data, lambda item: item.start
        ):
            if date >= now().date():
                return {"behälter": list(map(lambda item: item.summary, iterator))}
