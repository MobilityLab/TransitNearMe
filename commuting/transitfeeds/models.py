from django.contrib.gis.db import models
from stringfield import StringField

class Query(models.Model):
	provider_name = StringField()
	created = models.DateTimeField()
	success = models.BooleanField(default=False)

class BusPosition(models.Model):
	query = models.ForeignKey(Query)

	route_id = StringField()
	trip_id = StringField()
	vehicle_id = StringField()
	headsign = StringField()
	direction = models.IntegerField()
	direction_text = StringField()

	trip_start_time = models.DateTimeField()
	trip_end_time = models.DateTimeField()
	last_report_time = models.DateTimeField()
	deviation = models.FloatField()
	
	location = models.PointField()
	objects = models.GeoManager()

class RailPrediction(models.Model):
	query = models.ForeignKey(Query)

	location_id = StringField()
	location_name = StringField()
	group = models.IntegerField()
	
	line = StringField(null=True)
	destination_id = StringField(null=True)
	destination_name = StringField(null=True)
	minutes = StringField(null=True)
	cars = StringField(null=True)

