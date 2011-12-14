from django.contrib.gis.db import models
from stringfield import StringField

class Stop(models.Model):
    name = StringField(blank=True)
    location = models.PointField()
    api_cls = StringField()
    api_data = StringField(blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

class Prediction(models.Model):
    retrieved = models.DateTimeField()
    stop = models.ForeignKey(Stop)
    route = StringField(null=True)
    destination = StringField(null=True)
    wait = StringField(null=True)

    def __unicode__(self):
        return '%s %s %s' % (self.route, self.destination, self.wait)
