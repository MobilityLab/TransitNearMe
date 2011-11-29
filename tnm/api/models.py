from django.contrib.gis.db import models
from geojson import Feature, Point, LineString
from stringfield import StringField

from api.util import uniqify

class Dataset(models.Model):
    name = StringField()
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.name

class DatasetModel(models.Model):
    dataset = models.ForeignKey(Dataset)

    class Meta:
        abstract = True

class GtfsModel(DatasetModel):
    gtfs_id = StringField(blank=True)

    class Meta:
        abstract = True

class Agency(GtfsModel):
    json_fields = ['id', 'name']

    name = StringField()

    def __unicode__(self):
	return self.name

class Route(GtfsModel):
    json_fields = ['id', 'agency', 'name', 'route_type', 'color']

    agency = models.ForeignKey(Agency)
    name = StringField()
    route_type = models.IntegerField()
    color = StringField(null=True)

    def __unicode__(self):
	return self.name

class Stop(GtfsModel):
    json_fields = ['id', 'name', 'location']
    
    name = StringField()
    location = models.PointField()
    objects = models.GeoManager()

    def __unicode__(self):
	return self.name

class RouteSegment(DatasetModel):
    line = models.LineStringField(null=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return str(self.id)

class Pattern(DatasetModel):
    json_fields = ['id', 'route']

    route = models.ForeignKey(Route)
    origin = models.ForeignKey(Stop, related_name='pattern_origin')
    destination = models.ForeignKey(Stop, related_name='pattern_destination')
    stops = models.ManyToManyField(Stop, through='PatternStop')
    segments = models.ManyToManyField(RouteSegment)

    def __unicode__(self):
	return '%s: %s from %s to %s' % (self.id, self.route.name, self.origin.name, self.destination.name)

class PatternStop(DatasetModel):
    pattern = models.ForeignKey(Pattern)
    stop = models.ForeignKey(Stop)
    pattern_index = models.IntegerField()
    is_first_stop = models.BooleanField(default=False)
    is_last_stop = models.BooleanField(default=False)

    def __unicode__(self):
	return '%s #%s: %s' % (self.pattern.id, self.pattern_index, self.stop.name)

