import gpolyencode

from base64 import b64encode
from django.contrib.gis.db import models
from stringfield import StringField

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

class Stop(models.Model):
    name = StringField()
    location = models.PointField()
    predictions = models.ManyToManyField('transitapis.Stop')
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
        jd = {'id': self.id,
              'name': self.name,
              'location': self.location,
              'has_predictions': False}
        if self.id:
            jd['has_predictions'] = len(self.predictions.all()) > 0
        return jd

class Route(models.Model):
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
        return {'id': self.id,
                'agency': self.agency.name,
                'short_name': self.short_name,
                'long_name': self.long_name,
                'route_type': self.route_type,
                'color': self.color}

class RouteSegment(models.Model):
    line = models.LineStringField()
    line_encoded = StringField(null=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return str(self.id)

    def json_dict(self):
        return {'id': self.id,
                'line_encoded': self.line_encoded}

    def save(self, *args, **kwargs):
        encoder = gpolyencode.GPolyEncoder()
        self.line_encoded = encoder.encode(self.line.coords)['points']
        super(RouteSegment, self).save(*args, **kwargs)
        

class ServiceFromStop(models.Model):
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
        jd = {'id': self.id,
              'stop': self.stop.id,
              'route': self.route.id,
              'destination': self.destination.name,
            }
        if self.id:
            segment_ids = [v['id'] for v in self.segments.values('id')]
            jd.update({'segments': segment_ids})
        return jd
