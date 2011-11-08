from django.contrib.gis.db import models
from geojson import Feature, Point, LineString
from stringfield import StringField
from api.util import uniqify

class Agency(models.Model):
	name = StringField()

	def __unicode__(self):
		return self.name

class Route(models.Model):
	agency = models.ForeignKey(Agency)
	name = StringField()
	route_type = models.IntegerField()
	color = StringField(null=True)
	objects = models.GeoManager()

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
		return Route.objects.filter(pattern__patternstop__stop=self).distinct()

	@property
	def feature(self):
		routes = self.routes
		return Feature(geometry=Point(coordinates=[self.geom.x, self.geom.y]),
					   properties={'name': self.name,
								   'route_names': uniqify([route.name for route in routes]),
								   'route_types': uniqify([route.route_type for route in routes])},
					   id=self.id)

class Pattern(models.Model):
	route = models.ForeignKey(Route)
	geom = models.LineStringField(null=True)
	objects = models.GeoManager()

	@property
	def destination(self):
		return PatternStop.objects.filter(pattern=self, is_last_stop=True)[0]

	@property
	def feature(self):
		return Feature(geometry=LineString(self.geom.coords),
					   properties={'color': self.route.color,
								   'name': self.route.name,
								   'route_type': self.route.route_type,
								   'destination': self.destination.stop.name},
					   id=self.id)
	
	def __unicode__(self):
		return '%s pattern %s' % (self.route.name, str(self.id))

class PatternStop(models.Model):
	class Meta:
		unique_together = ('pattern', 'pattern_index')

	pattern = models.ForeignKey(Pattern)
	stop = models.ForeignKey(Stop)
	pattern_index = models.IntegerField()
	pattern_dist_pct = models.FloatField()
	is_first_stop = models.BooleanField(default=False)
	is_last_stop = models.BooleanField(default=False)
	objects = models.GeoManager()

	def __unicode__(self):
		return '%s # %d: %s' % (self.pattern, self.pattern_index, self.stop)

