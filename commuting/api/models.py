from django.contrib.gis.db import models
from geojson import Feature, Point, LineString
from stringfield import StringField
from api.util import uniqify

class Agency(models.Model):
	agency_id = models.IntegerField(primary_key=True)
	name = StringField()

	def __unicode__(self):
		return self.name

class Route(models.Model):
	agency = models.ForeignKey(Agency)
	name = StringField()
	type = models.IntegerField()
	color = StringField(null=True)

	def __unicode__(self):
		return self.name

class Stop(models.Model):
	name = StringField()
	
	geom = models.PointField()
	objects = models.GeoManager()

	def __unicode__(self):
		return self.name

	@property
	def routes(self):
		return Route.objects.filter(routestop__stop=self)

	@property
	def feature(self):
		return Feature(geometry=Point(coordinates=[self.geom.x, self.geom.y]),
					   properties={'name': self.name,
								   'route_names': uniqify([route.name for route in self.routes]),
								   'route_types': uniqify([route.type for route in self.routes])},
					   id=self.id)

class Pattern(models.Model):
	route = models.ForeignKey(Route)
	geom = models.LineStringField(null=True)
	objects = models.GeoManager()

	@property
	def feature(self):
		return Feature(geometry=LineString(self.geom.coords),
					   properties={'color': self.color,
								   'route_name': self.route.name},
					   id=self.id)
	
	def __unicode__(self):
		return '%s pattern %s' % (self.route.name, str(self.id))

class PatternStop(models.Model):
	class Meta:
		unique_together = ('pattern', 'pattern_index')

	pattern = models.ForeignKey(Pattern)
	stop = models.ForeignKey(Stop)
	pattern_index = models.IntegerField()
	is_first_stop = models.BooleanField(default=False)
	is_last_stop = models.BooleanField(default=False)

	def __unicode__(self):
		return '%s # %d: %s' % (self.pattern, self.pattern_index, self.stop)
