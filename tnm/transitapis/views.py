import json

from api.util import CustomJSONEncoder
from django.conf import settings
from django.contrib.gis.geos import Point, LinearRing
from django.http import HttpResponse, HttpResponseBadRequest
from transitapis.models import Stop

def predictable(request):
    nwLat = request.GET.get('nwLat', None)
    nwLng = request.GET.get('nwLng', None)
    seLat = request.GET.get('seLat', None)
    seLng = request.GET.get('seLng', None)

    if (nwLat is None) or (nwLng is None) or (seLat is None) or (seLng is None):
        return HttpResponseBadRequest('Missing parameters')

    nwPoint = Point(x=float(nwLng), y=float(nwLat), srid=4326)
    nePoint = Point(x=float(seLng), y=float(nwLat), srid=4326)
    sePoint = Point(x=float(seLng), y=float(seLat), srid=4326)
    swPoint = Point(x=float(nwLng), y=float(seLat), srid=4326)

    box = LinearRing(nwPoint, nePoint, sePoint, swPoint, nwPoint)
    stops = Stop.objects.filter(location__contained=box)

    stop_data = []
    for stop in stops:
        stop_data.append({
            'id': stop.id,
            'name': stop.name,
            'lat': stop.location.y,
            'lng': stop.location.x});
    data = json.dumps(stop_data, cls=CustomJSONEncoder)
    return HttpResponse(data, content_type='application/json') 

def predictions(request):
    stops_query = request.GET.get('stops', None)
    if stops_query is None:
        return HttpResponseBadRequest('Missing parameters')

    # Set up API methods.
    api_methods = {}
    for k,v in settings.TRANSIT_API_SOURCES.iteritems():
        api_id = k
        methods = v.get('methods', {})
        if not methods:
            continue

        options = v.get('options', {})
        for method in methods:
            parts = method.split('.')
            cls = __import__('.'.join(parts[:-1]))
            for part in parts[1:]:
                cls = getattr(cls, part)

            api_methods[api_id] = cls(id=api_id, options=options)

    stop_ids = [int(stop_id) for stop_id in stops_query.split(',')]
    stops = Stop.objects.filter(id__in=stop_ids)

    predictions = []
    for stop in stops:
        api_method = api_methods[stop.api_id]
        stop_predictions = api_method.get_predictions(stop)
        for stop_prediction in stop_predictions:
            predictions.append({
                'id': stop.id,
                'name': stop.name,
                'location': stop.location,
                'route': stop_prediction.route,
                'destination': stop_prediction.destination,
                'wait': str(stop_prediction.wait)
            })
        
    data = json.dumps(predictions, cls=CustomJSONEncoder)
    return HttpResponse(data, content_type='application/json')
