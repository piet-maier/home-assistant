import datetime

from aiohttp import ClientSession
from homeassistant.components.calendar import CalendarEvent
from yarl import URL


class RSAG:
    """This is a client for the web API of the Rhein-Sieg-Abfallwirtschaftsgesellschaft."""

    _URL = URL("https://www.rsag.de/api")

    def __init__(self, client: ClientSession):
        self._web_session = client

    async def fetch_data(self, city: str, street: str):
        """This method fetches pick-up dates for various waste container types.

        Args:
            city:
                This is the name of the city for which to fetch data.
            street:
                This is the name of the street for which to fetch data.

        Returns:
            The method returns a list of `CalendarEvent` objects in ascending order.

        Raises:
            ValueError:
                The method raises a `ValueError` if the city or street does not exist.
        """
        id = await self._get_street_id(await self._get_city_id(city), street)

        date = datetime.date.today()

        response = await self._web_session.get(
            self._URL
            / "pickup"
            / "filter"
            / str(id)
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

    async def _get_city_id(self, city: str) -> int:
        response = await self._web_session.get(self._URL / "city" / "all")

        async with response:
            data = await response.json()

            for item in data:
                if item["name"] == city:
                    return item["city_id"]

        raise ValueError(f'The city "{city}" does not exist.')

    async def _get_street_id(self, city: int, street: str) -> int:
        response = await self._web_session.get(
            self._URL / "street" / "filter" / str(city)
        )

        async with response:
            data = await response.json()

            for item in data:
                if item["name"] == street:
                    return item["street_id"]

        raise ValueError(f'The street "{street}" does not exist in city {city}.')
