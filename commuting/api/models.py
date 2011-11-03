from django.contrib.gis.db import models
from geojson import Feature, Point
from stringfield import StringField

class Stop(models.Model):
	stop_id = models.IntegerField(primary_key=True)
	stop_name = StringField()
	route_type = models.IntegerField()
	
	geom = models.PointField()
	objects = models.GeoManager()

	def __unicode__(self):
		return self.stop_name

	@property
	def feature(self):
		return Feature(geometry=Point(coordinates=[self.geom.x, self.geom.y]),
					   properties={'stop_name': self.stop_name,
								   'route_type': self.route_type},
					   id=self.stop_id)
	
