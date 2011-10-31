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

