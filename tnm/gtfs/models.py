from django.contrib.gis.db import models
from stringfield import StringField

class Dataset(models.Model):
    name = StringField()
    md5 = StringField()
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.md5)

class DatasetModel(models.Model):
    dataset = models.ForeignKey(Dataset)

    class Meta:
        abstract = True

class Agency(DatasetModel):
    agency_id = StringField(null=True, blank=True)
    agency_name = StringField()

    class Meta:
       verbose_name_plural = 'Agencies' 
    
    def __unicode__(self):
        return self.agency_name

class Stop(DatasetModel):
    stop_id = StringField()
    stop_name = StringField()
    location = models.PointField()
    objects = models.GeoManager()

    def __unicode__(self):
        return self.stop_name

class Route(models.Model):
    route_id = StringField()
    agency = models.ForeignKey(Agency, null=True, blank=True)
    route_short_name = StringField()
    route_long_name = StringField()
    route_type = StringField()
    route_color = StringField(null=True, blank=True)

    @property
    def name(self):
        if self.route_short_name and self.route_long_name:
            return '%s (%s)' % (self.route_short_name, self.route_long_name)
        if self.route_long_name:
            return self.route_long_name
        if self.route_short_name:
            return self.route_short_name
        return '%s (unknown name)' % self.id
    
    def __unicode__(self):
        if self.agency:
            return '%s %s' % (self.agency, self.name)
        return self.name

class Shape(DatasetModel):
    shape_ids = StringField()
    line = models.LineStringField()

    def __unicode__(self):
        return 'Shape %s' % self.shape_ids

class Pattern(models.Model):
    route = models.ForeignKey(Route)
    stops = models.ManyToManyField(Stop, through='PatternStop')
    shape = models.ForeignKey(Shape, null=True, blank=True)

    def __unicode__(self):
        stops = self.patternstop_set.order_by('order')
        return '%s from %s to %s' % (self.route, stops[0], stops[len(stops)-1])

class PatternStop(models.Model):
    pattern = models.ForeignKey(Pattern)
    stop = models.ForeignKey(Stop)
    order = models.IntegerField()

    def __unicode__(self):
        return '%s' % self.stop

class PatternStopTime(models.Model):
    patternstop = models.ForeignKey(PatternStop)
    trip_id = StringField()
    arrival_time = models.DateTimeField()
    departure_time = models.DateTimeField()
    
    def __unicode__(self):
        return '%s %s %s %s' % (patternstop, trip_id, arrival_time, departure_time)
