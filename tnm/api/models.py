import json

from api.util import CustomJSONEncoder
from django.contrib.gis.db import models
from stringfield import StringField

class JsonModel(models.Model):
    json = StringField(null=True, blank=True, editable=False)

    class Meta:
        abstract = True    

    def json_dict(self):
        pass

    def save(self, *args, **kwargs):
        save_json = kwargs.get('json', False)
        if 'json' in kwargs:
            del kwargs['json']
        if save_json or self.json:
            self.json = json.dumps(self.json_dict(),
                                   cls=CustomJSONEncoder)
        super(JsonModel, self).save(*args, **kwargs)

class Agency(models.Model):
    name = StringField()
    
    class Meta:
        verbose_name_plural = 'Agencies'

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Agency, self).save(*args, **kwargs)
        try:
            # Regenerate route JSON, if it exists.
            for route in self.route_set.iterator():
                route.save()
        except:
            pass

class Stop(JsonModel):
    name = StringField()
    location = models.PointField()
    objects = models.GeoManager()

    class Meta:
        ordering = ['name']

    @property
    def latitude(self):
        return self.location.y

    @latitude.setter
    def latitude(self, y):
        self.location.y = y

    @property
    def longitude(self):
        return self.location.x

    @longitude.setter
    def longitude(self, x):
        self.location.x = x

    def __unicode__(self):
        return self.name

    def json_dict(self):
        return {'name': self.name,
                'location': self.location}

class Route(JsonModel):
    agency = models.ForeignKey(Agency)
    short_name = StringField(null=True, blank=True)
    long_name = StringField(null=True, blank=True)
    route_type = models.IntegerField()
    color = StringField(null=True, blank=True)

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

class RouteSegment(models.Model):
    line = models.LineStringField(null=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return str(self.id)

class ServiceFromStop(JsonModel):
    stop = models.ForeignKey(Stop, related_name='services_leaving')
    route = models.ForeignKey(Route)
    destination = models.ForeignKey(Stop, related_name='services_finishing')
    segments = models.ManyToManyField(RouteSegment)
    objects = models.GeoManager()
    
    class Meta:
        verbose_name_plural = 'Stop services'

    def __unicode__(self):
        return '%s from %s to %s' % (self.route.name, self.stop.name, self.destination.name)

    def json_dict(self):
        d = {'stop': self.stop.id,
             'route': self.route.id,
             'destination': self.destination.name,
             'segments': []
            }
        if self.id:
            d['segments'] = [s.line for s in self.segments.all()]
        return d

