from django.shortcuts import render
from .backend import process_user_query, search_places
import asyncio

def index(request):
    error = None
    result = None
    locations = None

    if request.method == 'POST' and 'location' in request.POST:
        query = request.POST.get('location')
        locations = asyncio.run(search_places(query))

        if 'error' in locations:
            error = locations['error']
            locations = None

        request.session['locations'] = locations
    elif 'locations' in request.session:
        locations = request.session['locations']

    if request.method == 'POST' and 'selected_location' in request.POST:
        selected_location = request.POST.get('selected_location')
        name, lat, lon, country = selected_location.split('|')
        result = asyncio.run(process_user_query(name, lat, lon, country))

        if 'error' in result:
            error = result['error']
            result = None

    return render(request, 'myapp/index.html', {'locations': locations, 'result': result, 'error': error})
