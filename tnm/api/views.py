import json
import logging
import time

from django.contrib.gis.geos import Point, LineString
from django.contrib.gis.measure import D, Distance
from django.core.serializers import serialize
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.views.generic import View

from api.models import Stop, ServiceFromStop

class JSONResponseMixin(object):
    def render_to_response(self, content):
        data = json.dumps(content, cls=JSONResponseMixin.JSONEncoder)
        return HttpResponse(data, content_type='application/json')

    class JSONEncoder(json.JSONEncoder):
        def default(self, obj):
            try:
                iterable = iter(obj)
            except TypeError:
                pass
            else:
                return list(obj)

            if isinstance(obj, Point):
                return dict([d, getattr(obj, d)] for d in ['x', 'y', 'srid'])
            if isinstance(obj, LineString):
                # TODO: replace with encoded polyline here.
                return str(obj)
            if isinstance(obj, Distance):
                return obj.m
            return json.JSONEncoder.default(self, obj)

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

        # Collect stops, destinations, routes, and services.
        stops = {}
        destinations = {}  
        routes = {}
        for s in closest_services.values():
            if s.stop.id not in stops:
                stops[s.stop.id] = s.stop.json_dict()
            if s.destination.id not in destinations:
                destinations[s.destination.id] = s.destination.json_dict()
            if s.route.id not in routes:
                routes[s.route.id] = s.route.json_dict()
        services = [s.json_dict() for s in closest_services.values()]

        return {'stops': stops,
                'destinations': destinations,
                'routes': routes,
                'services': services}
