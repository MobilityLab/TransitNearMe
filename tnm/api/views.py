import geojson

from django.contrib.gis.geos import Point, LineString
from django.contrib.gis.measure import D
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.views.generic import View

from api.models import Stop, Route, Pattern, PatternStop
from api.util import uniqify

class GeoJSONResponseMixin(object):
	def render_to_response(self, content):
		return HttpResponse(geojson.dumps(content),
							content_type='application/json')

class BaseAPIView(GeoJSONResponseMixin, View):
	params = ['lat', 'lng', 'radius_m']
	required_params = params

	def get(self, request, *args, **kwargs):
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
		api_result = self.get_api_result(*args, **kwargs)
		
		# Return the result.
		return self.render_to_response(api_result)
	
class NearbyStopsView(BaseAPIView):
	def get_api_result(self, *args, **kwargs):
		stops = Stop.objects.filter(geom__distance_lte=(self.origin, 
													    D(m=self.radius_m)))
		return geojson.FeatureCollection([stop.as_feature() for stop in stops])

class NearbyView(BaseAPIView):
	def get_api_result(self, *args, **kwargs):
		features = []

		# Find all stops nearby.
		stops = Stop.objects.filter(geom__distance_lte=(self.origin,
														D(m=self.radius_m)))
		ordered_stops = stops.distance(self.origin).order_by('distance')	
		features.extend([stop.as_feature() for stop in ordered_stops])
	
		# Find all patterns that include one of these stops.
		patterns = Pattern.objects.filter(patternstop__stop__in=stops).distinct()

		# Find the closest stop on each pattern.
		for pattern in patterns:
			closest_stop = ordered_stops.filter(patternstop__pattern=pattern)[0]
			closest_stop_on_pattern = PatternStop.objects.get(
				pattern=pattern, 
				stop=closest_stop)
			
			if closest_stop_on_pattern.is_last_stop:
				continue
			
			geom_offset = closest_stop_on_pattern.pattern_dist_pct
			features.append(pattern.as_feature(geom_offset=geom_offset))

		return geojson.FeatureCollection(features)
