from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client.rsag import RSAG
from .const import DOMAIN
from .coordinator import AbfallCoordinator

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    coordinator = AbfallCoordinator(
        hass, config_entry, RSAG(async_get_clientsession(hass))
    )

    hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    result = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

    if result:
        hass.data.pop(DOMAIN, None)

    return result
