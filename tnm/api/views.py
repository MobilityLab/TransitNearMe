import json
import logging
import time

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db import connection
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.views.generic import View

from api.models import ServiceFromStop, Stop, Route, RouteSegment
from api.util import CustomJSONEncoder

from transitapis.apis import get_apis

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
        
        if not stop.has_predictions:
            return stop

        jd = stop.json_dict()
        
        try:
            apis = get_apis()
            logger = logging.getLogger('predictions')

            predictions = {}
            for prediction in stop.predictions.all():
                api = apis.get(prediction.api_name, None)
                if not api:
                    continue

                api_predictions = api.get_predictions(prediction)
                for api_prediction in api_predictions:
                    
                    logdata = {
                        'stop_id': stop.id,
                        'api_name': prediction.api_name,
                        'api_stop_id': prediction.id,
                        'stop_name': prediction.name,
                        'route': api_prediction.route,
                        'destination': api_prediction.destination,
                        'wait': api_prediction.wait
                    }
                    logger.info('%(stop_id)s %(api_stop_id)s "%(stop_name)s" "%(route)s" "%(destination)s" "%(wait)s"' % logdata) 

                    route_dest_pair = (api_prediction.route, api_prediction.destination)
                    if route_dest_pair not in predictions:
                        predictions[route_dest_pair] = []
                    predictions[route_dest_pair] += [api_prediction.wait]
           
            if predictions:
                jd['predictions'] = [{
                    'route': k[0],
                    'destination': k[1],
                    'waits': v} for (k,v) in predictions.iteritems()]
                    
        except Exception as ex:
            print ex
            pass
                
        return jd

class LocationAPIView(BaseAPIView):
    params = ['lat', 'lng', 'radius_m']
    required_params = params
 
class NearbyStopsView(LocationAPIView):
    def get_api_result(self, *args, **kwargs):
        stops = Stop.objects.filter(location__distance_lte=(
            Point(self.lng, self.lat, srid=4326),
            D(m=self.radius_m)))
        
        return [s.json_dict() for s in stops]
    
class NearbyView(LocationAPIView):
    def get_api_result(self, *args, **kwargs):
        origin = Point(self.lng, self.lat, srid=4326)
        radius = self.radius_m
       
        query = 'SELECT sfs.id, sfs.stop_id, sfs.route_id, sfss.routesegment_id FROM (SELECT sfs.route_id, sfs.destination_id, min(ST_Distance_Sphere(api_stop.location, ST_GeomFromEWKB(%s))) as "mindistance" FROM api_stop INNER JOIN api_servicefromstop sfs ON api_stop.id = sfs.stop_id WHERE ST_Distance_Sphere(api_stop.location, ST_GeomFromEWKB(%s)) <= %s AND api_stop.id != sfs.destination_id GROUP BY sfs.route_id, sfs.destination_id) AS closest INNER JOIN api_servicefromstop sfs ON sfs.route_id = closest.route_id AND sfs.destination_id = closest.destination_id INNER JOIN api_stop ON sfs.stop_id = api_stop.id AND ST_Distance_Sphere(api_stop.location, ST_GeomFromEWKB(%s)) = closest.mindistance INNER JOIN api_route ON sfs.route_id = api_route.id LEFT OUTER JOIN api_servicefromstop_segments sfss ON sfs.id = sfss.servicefromstop_id'
        args = [origin.ewkb, origin.ewkb, radius, origin.ewkb]

        cursor = connection.cursor()
        cursor.execute(query, args)
        data = cursor.fetchall()

        servicefromstop_ids = [row[0] for row in data]
        stop_ids = [row[1] for row in data]
        route_ids = [row[2] for row in data]
        routesegment_ids = [row[3] for row in data]

        services = ServiceFromStop.objects.filter(id__in=servicefromstop_ids)
        stops = Stop.objects.filter(id__in=stop_ids)
        routes = Route.objects.filter(id__in=route_ids)
        routesegments = RouteSegment.objects.filter(id__in=routesegment_ids)

        return {
            'services': services,
            'stops': stops,
            'routes': routes,
            'segments': routesegments
        }
