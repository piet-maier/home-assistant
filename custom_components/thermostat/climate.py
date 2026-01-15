import logging
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
from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.group.entity import GroupEntity
from homeassistant.components.group.util import find_state_attributes, reduce_attribute
from homeassistant.components.number.const import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.components.number.const import DOMAIN as NUMBER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_ENTITIES,
    CONF_NAME,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.event import async_track_state_change_event

from .const import SENSOR

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

    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        entities: list[str],
        sensor: str | None,
    ):
        self.hass = hass

        self._attr_name = name
        self._attr_unique_id = entry_id

        self._entity_ids = entities

        self._attr_temperature_unit = self.hass.config.units.temperature_unit

        self._sensor_id = sensor

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        if self._sensor_id is None:
            return

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._sensor_id, self._async_sensor_state_change
            )
        )

    @callback
    async def _async_sensor_state_change(
        self, state_change: Event[EventStateChangedData]
    ):
        if state_change.data["new_state"] is None:
            return

        sensor_state = state_change.data["new_state"].state

        if sensor_state in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
            return

        sensor_value = float(sensor_state)

        _LOGGER.info(
            'Setting external_temperature_input of "%s" to %.1f %s...',
            self._attr_name,
            sensor_value,
            self._attr_temperature_unit,
        )

        registry = async_get(self.hass)

        for group_entity in map(registry.async_get, self._entity_ids):
            if group_entity is None or group_entity.device_id is None:
                continue

            for entity in registry.entities.values():
                if (
                    group_entity.device_id != entity.device_id
                    or entity.domain != NUMBER_DOMAIN
                    or "external_temperature_input" not in entity.entity_id
                ):
                    continue

                await self.hass.services.async_call(
                    NUMBER_DOMAIN,
                    SERVICE_SET_VALUE,
                    {ATTR_ENTITY_ID: entity.entity_id, ATTR_VALUE: sensor_value},
                    True,
                    self._context,
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
            states, ATTR_CURRENT_TEMPERATURE
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
        data = {ATTR_HVAC_MODE: hvac_mode}

        await self._async_call_service_action(SERVICE_SET_HVAC_MODE, data)

    async def async_turn_on(self):
        data = {ATTR_HVAC_MODE: HVACMode.HEAT}

        await self._async_call_service_action(SERVICE_TURN_ON, data)

    async def async_turn_off(self):
        data = {ATTR_HVAC_MODE: HVACMode.OFF}

        await self._async_call_service_action(SERVICE_TURN_OFF, data)

    async def async_toggle(self):
        if self.state != HVACMode.OFF:
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    async def async_set_temperature(self, **kwargs: typing.Any):
        data = {ATTR_TEMPERATURE: kwargs[ATTR_TEMPERATURE]}

        await self._async_call_service_action(SERVICE_SET_TEMPERATURE, data)

    async def _async_call_service_action(self, name: str, data: dict[str, typing.Any]):
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            name,
            {ATTR_ENTITY_ID: self._entity_ids} | data,
            True,
            self._context,
        )
