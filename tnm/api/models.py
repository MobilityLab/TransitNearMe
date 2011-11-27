from django.contrib.gis.db import models
from geojson import Feature, Point, LineString
from stringfield import StringField
from api.util import uniqify

class Dataset(models.Model):
    created = models.DateTimeField(auto_now_add=True)

class Agency(models.Model):
    dataset = models.ForeignKey(Dataset)
    gtfs_id = StringField(blank=True)
    name = StringField()

    def __unicode__(self):
	return self.name

class Route(models.Model):
    dataset = models.ForeignKey(Dataset)
    gtfs_id = StringField(blank=True)
    agency = models.ForeignKey(Agency)
    name = StringField()
    route_type = models.IntegerField()
    color = StringField(null=True)
    objects = models.GeoManager()

    def __unicode__(self):
	return self.name

class Stop(models.Model):
    dataset = models.ForeignKey(Dataset)
    gtfs_id = StringField(blank=True)
    name = StringField()

    geom = models.PointField()
    objects = models.GeoManager()

    def __unicode__(self):
	return self.name

    @property
    def routes(self):
    	return Route.objects.filter(pattern__patternstop__stop=self).distinct()

    def as_feature(self):
    	routes = self.routes
    	return Feature(geometry=Point(
            coordinates=[self.geom.x, self.geom.y]),
    	    properties={'id': self.id,
                        'name': self.name,
                        'patterns': uniqify([p.id for p in Pattern.objects.filter(patternstop__stop=self)]),
			'route_names': uniqify([route.name for route in routes]),
			'route_types': uniqify([route.route_type for route in routes])},
	    id=self.id)

class Pattern(models.Model):
    dataset = models.ForeignKey(Dataset)
    route = models.ForeignKey(Route)
    
    geom = models.LineStringField(null=True)
    objects = models.GeoManager()

    @property
    def destination(self):
    	return PatternStop.objects.filter(pattern=self, is_last_stop=True)[0]

    def as_feature(self, geom_offset=None):
    	coords = self.geom.coords
    	if geom_offset:
    	    coords = coords[int(len(coords) * geom_offset):]
	
        return Feature(
            geometry=LineString(coords),
    	    properties={'id': self.id,
                        'color': self.route.color,
                        'name': self.route.name,
                        'route_type': self.route.route_type,
                        'destination': self.destination.stop.name,
			'stops': uniqify([s.id for s in Stop.objects.filter(patternstop__pattern=self)])},
		id=self.id)
	
	def __unicode__(self):
	    return '%s pattern %s' % (self.route.name, str(self.id))

class PatternStop(models.Model):
    class Meta:
	unique_together = ('pattern', 'pattern_index')

    dataset = models.ForeignKey(Dataset)
    pattern = models.ForeignKey(Pattern)
    stop = models.ForeignKey(Stop)
    pattern_index = models.IntegerField()
    is_first_stop = models.BooleanField(default=False)
    is_last_stop = models.BooleanField(default=False)
    objects = models.GeoManager()

    def __unicode__(self):
	return '%s # %d: %s' % (self.pattern, self.pattern_index, self.stop)

