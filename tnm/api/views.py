import json
import logging
import time

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
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
        origin = Point(self.lng, self.lat)    
        services = ServiceFromStop.objects.select_related().filter(stop__location__distance_lte=(
            origin,
            D(m=self.radius_m)))

        # Find closest option for each service/destination.
        services = services.distance(origin, field_name='stop__location')
        closest_services = {}
        for service in services:
            pair = (service.route, service.destination)
            closest = closest_services.get(pair, None)
            if not closest or service.distance < closest.distance:
                closest_services[pair] = service

        # Collect stops, routes, and services.
        stops = {}
        routes = {}
        for s in closest_services.values():
            if s.stop.id not in stops:
                stops[s.stop.id] = json.loads(s.stop._json)
            if s.route.id not in routes:
                routes[s.route.id] = json.loads(s.route._json)
        services = [json.loads(s._json) for s in closest_services.values()]

        return {'stops': stops,
                'routes': routes,
                'services': services}
