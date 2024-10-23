import aiohttp
import asyncio

LIMIT = 10
RADIUS = 1000

async def get_locations(query):
    url = 'https://graphhopper.com/api/1/geocode'
    myParams = {"q": query, "key": "45cae03b-4504-49ad-af0b-0b018fbc9b82", "limit": LIMIT}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=myParams) as response:
                if response.status != 200:
                    raise Exception(f"HTTP error in get locations: {response.status}")
                return await response.json()
    except Exception as e:
        return {'error': str(e)}
        
async def get_weather(lat, lon):
    url = 'https://api.openweathermap.org/data/2.5/weather'
    myParams = {"lat": lat, "lon": lon, "appid": "4059cf463d79ea85b27e740de3ba59d8"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=myParams) as response:
                if response.status != 200:
                    raise Exception(f"HTTP error in get weather: {response.status}")
                return await response.json()
    except Exception as e:
        return {'error': str(e)}
        
async def get_places(lat, lon):
    url = 'https://api.opentripmap.com/0.1/en/places/radius'
    apiKey = "5ae2e3f221c38a28845f05b6301dc5477ec5c8b935bd2cd6baf0dba0"
    myParams = {"lat": lat, "lon": lon, "apikey": apiKey, "radius": RADIUS}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=myParams) as response:
                if response.status != 200:
                    raise Exception(f"HTTP error in get places: {response.status}")
                return await response.json()
    except Exception as e:
        return {'error': str(e)}
        
async def get_place_description(xid):
    url = f'https://api.opentripmap.com/0.1/en/places/xid/{xid}'
    apiKey = "5ae2e3f221c38a28845f05b6301dc5477ec5c8b935bd2cd6baf0dba0"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"apikey": apiKey}) as response:
                if response.status != 200:
                    raise Exception(f"HTTP error in get place description: {response.status}")
                return await response.json()
    except Exception as e:
        return {'error': str(e)}
        
async def search_places(query):
    res_of_locations = await get_locations(query)

    if 'error' in res_of_locations:
        return res_of_locations

    return res_of_locations['hits']

async def process_user_query(name, lat, lon, country):
    weather_task = asyncio.create_task(get_weather(lat, lon))
    places_task = asyncio.create_task(get_places(lat, lon))
    
    res_of_weather = await weather_task
    res_of_places = await places_task

    if 'error' in res_of_weather:
        return res_of_weather
    if 'error' in res_of_places:
        return res_of_places

    places = res_of_places['features']

    desc_tasks = [get_place_description(place['properties']['xid']) for place in places]
    desc_results = await asyncio.gather(*desc_tasks)

    weather = res_of_weather['weather'][0]
    icon_code = weather['icon']
    url = f'https://openweathermap.org/img/wn/{icon_code}@2x.png'

    result = {
        'location': {'name': name, 'country': country},
        'weather': {'main': res_of_weather, 'weather': weather, 'url': url},
        'places': [{'place': place, 'description': desc} for place, desc in zip(places, desc_results)]
    }

    return result
