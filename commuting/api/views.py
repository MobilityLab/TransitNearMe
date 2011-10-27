from django.contrib.gis.geos import GEOSGeometry, GeometryCollection
from django.db import connection, transaction
from django.http import Http404, HttpResponse

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
