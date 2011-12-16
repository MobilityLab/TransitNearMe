import json

from django.conf import settings
from django.contrib.gis.geos import Point, LinearRing
from django.http import HttpResponse, HttpResponseBadRequest
from transitapis.apis import get_apis
from transitapis.models import Stop

def stops(request):
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

    stop_data = dict([(s.id, s.json_dict()) for s in stops])
    data = json.dumps(stop_data)
    return HttpResponse(data, content_type='application/json') 

def predictions(request):
    stops_query = request.GET.get('stops', None)
    if stops_query is None:
        return HttpResponseBadRequest('Missing parameters')

    apis = get_apis() 

    stop_ids = [int(stop_id) for stop_id in stops_query.split(',')]
    stops = Stop.objects.filter(id__in=stop_ids)

    prediction_data = {}
    for stop in stops:
        api = apis.get(stop.api_name, None)
        if not api:
            continue
    
        predictions = api.get_predictions(stop)
        if not len(predictions):
            continue

        prediction_data[stop.id] = [p.json_dict() for p in predictions]
        
    data = json.dumps(prediction_data)
    return HttpResponse(data, content_type='application/json')
