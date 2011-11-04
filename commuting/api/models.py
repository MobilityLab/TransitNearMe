from django.contrib.gis.db import models
from geojson import Feature, Point, LineString
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

class Pattern(models.Model):
	geom = models.LineStringField(null=True)
	objects = models.GeoManager()
	color = StringField(null=True)
	name = StringField(null=True)

	@property
	def feature(self):
		return Feature(geometry=LineString(self.geom.coords),
					   properties={'color': self.color},
					   id=self.id)

class PatternStop(models.Model):
	class Meta:
		unique_together = ('pattern', 'pattern_index')

	pattern = models.ForeignKey(Pattern)
	pattern_index = models.IntegerField()
	stop = models.ForeignKey(Stop)
	is_first_stop = models.BooleanField(default=False)
	is_last_stop = models.BooleanField(default=False)

	def __unicode__(self):
		return self.stop.stop_name
