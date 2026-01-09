from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_setups(
        config_entry, [Platform.CLIMATE]
    )

    return True
