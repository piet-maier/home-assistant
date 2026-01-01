import datetime

from aiohttp import ClientSession
from homeassistant.components.calendar import CalendarEvent
from yarl import URL


class RSAG:
    """This is a client for the web API of the Rhein-Sieg-Abfallwirtschaftsgesellschaft."""

    _URL = URL("https://www.rsag.de/api")

    def __init__(self, client: ClientSession):
        self._web_session = client

    async def async_fetch_data(self, street: int):
        """This method fetches pick-up dates for various waste container types.

        Args:
            street:
                This is the ID of the street for which to fetch data.

        Returns:
            The method returns a list of `CalendarEvent` objects in ascending order.
        """
        date = datetime.date.today()

        response = await self._web_session.get(
            self._URL
            / "pickup"
            / "filter"
            / str(street)
            / "1,2,3,4,6,7,8"
            / f"{str(date.month)},{str(date.month + 1)}"
        )

        async with response:
            data = await response.json()

            result: list[CalendarEvent] = []

            for period in data:
                for item in period["items"]:
                    date = datetime.date.fromisoformat(item["pickupdate"])

                    result.append(
                        CalendarEvent(
                            date,
                            date + datetime.timedelta(days=1),
                            item["wastetype_name"],
                        )
                    )

            return sorted(result, key=lambda item: item.start)
