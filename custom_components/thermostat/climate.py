import collections.abc
import datetime
import logging
import statistics
import typing

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.group.entity import GroupEntity
from homeassistant.components.group.util import find_state_attributes, reduce_attribute
from homeassistant.components.number.const import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_ENTITIES,
    CONF_NAME,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_entries_for_device, async_get
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .const import SENSOR, WINDOW

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    async_add_entities(
        [
            ThermostatEntity(
                hass,
                entry.entry_id,
                entry.data[CONF_NAME],
                entry.data[CONF_ENTITIES],
                entry.data.get(SENSOR),
                entry.data.get(WINDOW),
            )
        ]
    )


class ThermostatEntity(GroupEntity, ClimateEntity):
    _attr_available = False
    _attr_has_entity_name = True
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        entities: list[str],
        sensor: str | None,
        window: str | None,
    ):
        self.hass = hass

        self._attr_name = name
        self._attr_unique_id = entry_id

        self._entity_ids = entities

        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        self._attr_temperature_unit = self.hass.config.units.temperature_unit

        self._sensor_id = sensor

        self._sensor_callable: collections.abc.Callable[[], None] | None = None

        self._window_id = window

        self._window_callable: collections.abc.Callable[[], None] | None = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        if self._sensor_id is not None:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, self._sensor_id, self._async_sensor_state_change
                )
            )

        if self._window_id is not None:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, self._window_id, self._async_window_state_change
                )
            )

    async def _async_sensor_state_change(
        self, state_change: Event[EventStateChangedData] | None = None
    ):
        """This method sets the `external_temperature_input` value of all devices in the group.

        It is called when the value of the sensor entity referenced by `self._sensor_id` changes or 15 minutes have passed since its last invocation.

        Args:
            state_change:
                This is the state change event, or `None` if the method was called as a keep-alive.
        """
        if self._sensor_callable is not None:
            self._sensor_callable()

        if self._sensor_id is None:
            return

        state_object = (
            state_change.data["new_state"]
            if state_change is not None
            else self.hass.states.get(self._sensor_id)
        )

        if state_object is None:
            return

        state_string = state_object.state

        if state_string in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
            return

        state_number = float(state_string)

        _LOGGER.debug(
            'Setting external_temperature_input of "%s" to %.1f %s...',
            self._attr_name,
            state_number,
            self._attr_temperature_unit,
        )

        registry = async_get(self.hass)

        for group_entity in map(registry.async_get, self._entity_ids):
            if group_entity is None or group_entity.device_id is None:
                continue

            for entity in async_entries_for_device(registry, group_entity.device_id):
                if (
                    entity.domain != Platform.NUMBER
                    or "external_temperature_input" not in entity.entity_id
                ):
                    continue

                await self.hass.services.async_call(
                    Platform.NUMBER,
                    SERVICE_SET_VALUE,
                    {ATTR_ENTITY_ID: entity.entity_id, ATTR_VALUE: state_number},
                    True,
                    self._context,
                )

        async def action(_: datetime.datetime):
            await self._async_sensor_state_change()

        self._sensor_callable = async_call_later(
            self.hass, datetime.timedelta(minutes=15), action
        )

    async def _async_window_state_change(
        self, state_change: Event[EventStateChangedData]
    ):
        """This method turns all devices in the group on or off when a window is opened or closed and remains in that state for at least one minute.

        The method is called when the value of the binary sensor entity referenced by `self._window_id` changes.

        Args:
            state_change:
                This is the state change event.
        """
        if self._window_callable is not None:
            self._window_callable()

        if self._window_id is None:
            return

        state_object = state_change.data["new_state"]

        if state_object is None:
            return

        state_string = state_object.state

        if state_string in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
            return

        state_bool = state_string == STATE_ON

        mode = HVACMode.OFF if state_bool else HVACMode.HEAT

        if self.hvac_mode == mode:
            return

        async def action(_: datetime.datetime):
            _LOGGER.debug(
                'Setting HVAC mode of "%s" to %s because of a window state change...',
                self._attr_name,
                mode,
            )

            await self._async_call_service_action(
                SERVICE_SET_HVAC_MODE, {ATTR_HVAC_MODE: mode}
            )

        self._window_callable = async_call_later(
            self.hass, datetime.timedelta(minutes=1), action
        )

    @callback
    def async_update_group_state(self):
        states = list(self._entity_states())

        if all(item.state == STATE_UNAVAILABLE for item in states):
            self._attr_available = False

            return

        self._attr_available = True

        states = [
            item
            for item in states
            if item.state not in [STATE_UNAVAILABLE, STATE_UNKNOWN]
        ]

        if not states:
            self._attr_hvac_mode = None

            return

        if all(item.state == HVACMode.OFF for item in states):
            self._attr_hvac_mode = HVACMode.OFF

            self._attr_hvac_action = HVACAction.OFF
        else:
            self._attr_hvac_mode = HVACMode.HEAT

            if all(
                item == HVACAction.IDLE
                for item in find_state_attributes(states, ATTR_HVAC_ACTION)
            ):
                self._attr_hvac_action = HVACAction.IDLE
            else:
                self._attr_hvac_action = HVACAction.HEATING

        self._attr_current_temperature = reduce_attribute(
            states, ATTR_CURRENT_TEMPERATURE, reduce=mean
        )

        self._attr_max_temp = reduce_attribute(
            states, ATTR_MAX_TEMP, DEFAULT_MAX_TEMP, max
        )

        self._attr_min_temp = reduce_attribute(
            states, ATTR_MIN_TEMP, DEFAULT_MIN_TEMP, min
        )

        self._attr_target_temperature = reduce_attribute(states, ATTR_TEMPERATURE)

    def _entity_states(self):
        for entity in self._entity_ids:
            entity_state = self.hass.states.get(entity)

            if entity_state is not None:
                yield entity_state

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        if (
            hvac_mode == HVACMode.HEAT
            and self._window_id is not None
            and self.hass.states.is_state(self._window_id, STATE_ON)
        ):
            return

        data = {ATTR_HVAC_MODE: hvac_mode}

        await self._async_call_service_action(SERVICE_SET_HVAC_MODE, data)

    async def async_turn_on(self):
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_toggle(self):
        if self.state != HVACMode.OFF:
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    async def async_set_temperature(self, **kwargs: typing.Any):
        if self._window_id and self.hass.states.is_state(self._window_id, STATE_ON):
            return

        data = {ATTR_TEMPERATURE: kwargs[ATTR_TEMPERATURE]}

        await self._async_call_service_action(SERVICE_SET_TEMPERATURE, data)

    async def _async_call_service_action(self, name: str, data: dict[str, typing.Any]):
        await self.hass.services.async_call(
            Platform.CLIMATE,
            name,
            {ATTR_ENTITY_ID: self._entity_ids} | data,
            True,
            self._context,
        )


def mean(*data: float):
    return round(statistics.fmean(data), 1)
