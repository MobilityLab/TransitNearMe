from django.contrib.gis.db import models
from django.db import connection
from geojson import Feature, Point, loads as geojson_loads
from stringfield import StringField

class Stop(models.Model):
	class Meta:
		db_table = 'stops'

	stop_id = StringField(primary_key=True)
	stop_code = StringField(null=True)
	stop_name = StringField()
	stop_desc = StringField(null=True)
	stop_lat = models.FloatField() # numeric(12,9)
	stop_lon = models.FloatField() # numeric(12,9)
	zone_id = StringField(null=True)
	stop_url = StringField(null=True)
	location_type = models.IntegerField(default=0)
	parent_station = StringField(null=True)
	
	geom = models.PointField()
	objects = models.GeoManager()

	def __unicode__(self):
		return self.stop_name
	
	@property
	def route_type(self):
		cursor = connection.cursor()
		cursor.execute("SELECT routes.route_type FROM routes JOIN trips ON routes.route_id = trips.route_id JOIN stop_times ON trips.trip_id = stop_times.trip_id JOIN stops ON stop_times.stop_id = stops.stop_id WHERE stops.stop_id = '%s'", [int(self.stop_id)])
		return cursor.fetchone()[0]

	@property
	def feature(self):
		return Feature(geometry=Point(coordinates=[self.geom.x, self.geom.y]),
					   properties={'stop_name': self.stop_name,
								   'route_type': self.route_type}, 
					   id=self.stop_id)
