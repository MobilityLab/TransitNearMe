from django.contrib.gis.db import models
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

class RouteType(models.Model):
	class Meta:
		db_table = 'route_type'

	route_type = models.IntegerField(primary_key=True)
	route_type_name = StringField(null=True)
	route_type_desc = StringField(null=True)

class Route(models.Model):
	class Meta:
		db_table = 'routes'

	route_id = StringField(primary_key=True)
	agency_id = StringField(null=True)
	route_short_name = StringField(null=True)
	route_long_name = StringField(null=True)
	route_type = models.ForeignKey(RouteType,
								   db_column='route_type')
	route_url = StringField(null=True)
	route_color = StringField(null=True)
	route_text_color = StringField(null=True)

	geom = models.MultiLineStringField()
	objects = models.GeoManager()

	def __unicode__(self):
		return self.route_short_name
