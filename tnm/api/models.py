from django.contrib.gis.db import models
from django.core.urlresolvers import reverse
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
    name = StringField()

    def __unicode__(self):
        return self.name

class Stop(GtfsModel):
    name = StringField()
    location = models.PointField()
    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    def json_dict(self):
        return {'name': self.name,
                'location': self.location,
                'url': reverse('stop', args=[self.id])}

class Route(GtfsModel):
    agency = models.ForeignKey(Agency)
    short_name = StringField(null=True)
    long_name = StringField(null=True)
    route_type = models.IntegerField()
    color = StringField(null=True)

    @property
    def name(self):
        if self.short_name and self.long_name:
            return '%s (%s)' % (self.short_name, self.long_name)
        if self.long_name:
            return self.long_name
        if self.short_name:
            return self.short_name
        return '%s (unknown name)' % self.id

    def __unicode__(self):
        return self.name

    def json_dict(self):
        return {'agency': self.agency.name,
                'short_name': self.short_name,
                'long_name': self.long_name,
                'route_type': self.route_type,
                'color': self.color}

class RouteSegment(DatasetModel):
    line = models.LineStringField(null=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return str(self.id)

class ServiceFromStop(DatasetModel):
    stop = models.ForeignKey(Stop, related_name='service')
    route = models.ForeignKey(Route)
    destination = models.ForeignKey(Stop)
    segments = models.ManyToManyField(RouteSegment)
    objects = models.GeoManager()

    def __unicode__(self):
        return '%s from %s to %s' % (self.route.name, self.stop.name, self.destination.name)

    def json_dict(self):
        return {'stop': self.stop.id,
                'route': self.route.id,
                'destination': self.destination.name,
                'segments': [s.line for s in self.segments.all()]}

