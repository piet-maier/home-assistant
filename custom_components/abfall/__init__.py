from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "abfall"


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_setups(config_entry, ["calendar"])

    return True
