import geojson

from django.contrib.gis.geos import Point, GEOSGeometry, GeometryCollection
from django.contrib.gis.measure import D
from django.db import connection, transaction
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.views.generic import View

from gtfs.models import Stop

class GeoJSONResponseMixin(object):
	def render_to_response(self, content):
		return HttpResponse(geojson.dumps(content),
							content_type='application/json')

class BaseAPIView(GeoJSONResponseMixin, View):
	params = ['lat', 'lon', 'radius_m']
	required_params = params

	def get(self, request, *args, **kwargs):
		# Parse query params.	
		for param in self.params:
			if param in request.GET:
				setattr(self, param, float(request.GET[param]))

		for param in self.required_params:
			if param not in request.GET:
				return HttpResponseBadRequest('Required parameters: ' + ', '.join(self.required_params))

		if hasattr(self, 'lon') and hasattr(self, 'lat'):	
			self.origin = Point(self.lon, self.lat)
	
		# Perform the API call.
		api_result = self.get_api_result(*args, **kwargs)
		
		# Return the result.
		return self.render_to_response(api_result)
	
class NearbyStopsView(BaseAPIView):
	def get_api_result(self, *args, **kwargs):
		stops = Stop.objects.filter(geom__distance_lte=(self.origin, 
													   D(m=self.radius_m)))
		return geojson.FeatureCollection([stop.feature for stop in stops])

def nearby(request):
	lat = request.GET.get('lat', None)
	lon = request.GET.get('lon', None)
	distance_m = request.GET.get('distance', 1000)

	if not lat or not lon:
		raise Http404

	cursor = connection.cursor()	
	cursor.execute("SELECT ST_AsGeoJSON(ST_Collect(geom)) FROM stops WHERE ST_DWithin(ST_Transform(ST_GeomFromText('POINT(%s %s)', 4326), 32661), ST_Transform(geom, 32661), %s)", [float(lon), float(lat), float(distance_m)])
	stops_geojson = cursor.fetchone()[0]
	stops = GEOSGeometry(stops_geojson)
	
	cursor.execute("SELECT ST_AsGeoJSON(ST_Collect(geom)) FROM routes WHERE ST_DWithin(ST_Transform(ST_GeomFromText('POINT(%s %s)', 4326), 32661), ST_Transform(geom, 32661), %s)", [float(lon), float(lat), float(distance_m)])
	routes_geojson = cursor.fetchone()[0]
	routes = GEOSGeometry(routes_geojson)

	all_geos = []
	all_geos.append(stops)
	for route in routes:
		all_geos.append(route)

	all_geo = GeometryCollection(all_geos)
	return HttpResponse(all_geo.geojson, mimetype='application/json')
