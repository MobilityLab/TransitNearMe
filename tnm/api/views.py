import json
import logging
import time

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db import connection
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.views.generic import View

from api.models import Stop, ServiceFromStop
from api.util import CustomJSONEncoder

class JSONResponseMixin(object):
    def render_to_response(self, content):
        data = json.dumps(content, cls=CustomJSONEncoder)
        return HttpResponse(data, content_type='application/json')

class BaseAPIView(JSONResponseMixin, View):
    params = []
    required_params = params

    def get(self, request, *args, **kwargs):
        logger = logging.getLogger('api')
        
        # Parse query params.   
        for param in self.params:
            if param in request.GET:
                setattr(self, param, float(request.GET[param]))

        for param in self.required_params:
            if param not in request.GET:
                return HttpResponseBadRequest('Required parameters: ' + ', '.join(self.required_params))

        if hasattr(self, 'lng') and hasattr(self, 'lat'):       
            self.origin = Point(self.lng, self.lat)
        
        # Perform the API call.
        start = time.time()     
        api_result = self.get_api_result(*args, **kwargs)
        duration = time.time() - start

        logdata = { 
                'call': request.path,
                'params': request.META.get('QUERY_STRING', ''),
                'duration': duration,
                'ip': request.META.get('REMOTE_ADDR', ''),
                'ua': request.META.get('HTTP_USER_AGENT', '')
        }
        logger.info('%(call)s "%(params)s" %(duration).2f "%(ip)s" "%(ua)s"' % logdata)
                
        # Return the result.
        return self.render_to_response(api_result)

class StopView(BaseAPIView):
    def get_api_result(self, *args, **kwargs):
        try:
            stop = Stop.objects.get(pk=int(kwargs['id']))
        except Stop.DoesNotExist:
            raise Http404
            
        return {'id': stop.id,
                'name': stop.name,
                'location': stop.location}

class LocationAPIView(BaseAPIView):
    params = ['lat', 'lng', 'radius_m']
    required_params = params
 
class NearbyStopsView(LocationAPIView):
    def get_api_result(self, *args, **kwargs):
        stops = Stop.objects.filter(location__distance_lte=(
            Point(self.lng, self.lat),
            D(m=self.radius_m)))
        
        return [s.json_dict() for s in stops]
    
class NearbyView(LocationAPIView):
    def get_api_result(self, *args, **kwargs):
        origin = Point(self.lng, self.lat, srid=4326)
        radius = self.radius_m
        
        query = 'SELECT api_servicefromstop.stop_id, closest.route_id, closest.destination_id, api_servicefromstop._json as "service_json", api_stop._json as "stop_json", api_route._json as "route_json" FROM (SELECT api_servicefromstop.route_id, api_servicefromstop.destination_id, min(ST_Distance_Sphere(api_stop.location, ST_GeomFromEWKB(%s))) as "mindistance" FROM api_stop INNER JOIN api_servicefromstop ON api_stop.id = api_servicefromstop.stop_id WHERE ST_Distance_Sphere(api_stop.location, ST_GeomFromEWKB(%s)) <= %s AND api_stop.id != api_servicefromstop.destination_id GROUP BY api_servicefromstop.route_id, api_servicefromstop.destination_id) AS closest INNER JOIN api_servicefromstop ON api_servicefromstop.route_id = closest.route_id AND api_servicefromstop.destination_id = closest.destination_id INNER JOIN api_stop ON api_servicefromstop.stop_id = api_stop.id AND ST_Distance_Sphere(api_stop.location, ST_GeomFromEWKB(%s)) = closest.mindistance INNER JOIN api_route ON api_servicefromstop.route_id = api_route.id'
        args = [origin.ewkb, origin.ewkb, radius, origin.ewkb]

        cursor = connection.cursor()
        cursor.execute(query, args)

        data = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]
        stops = dict((d['stop_id'], json.loads(d['stop_json'])) for d in data)
        routes = dict((d['route_id'], json.loads(d['route_json'])) for d in data)
        services = [json.loads(d['service_json']) for d in data]
        return {
            'stops': stops,
            'routes': routes,
            'services': services
        }    
