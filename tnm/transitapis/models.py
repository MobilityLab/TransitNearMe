from django.contrib.gis.db import models
from stringfield import StringField

class Stop(models.Model):
    name = StringField(blank=True)
    location = models.PointField()
    api_name = StringField()
    api_data = StringField(blank=True)

    objects = models.GeoManager()

    def __unicode__(self):
        return self.name

    def json_dict(self):
        return {
            'name': self.name,
            'api_name': self.api_name,
            'lat': self.location.y,
            'lng': self.location.x,
            'code': self.api_name.lower().replace(' ','-') + ':' + self.api_data, # normalize to lower case without spaces
        }

            
class Prediction(models.Model):
    retrieved = models.DateTimeField()
    stop = models.ForeignKey(Stop)
    route = StringField(null=True)
    destination = StringField(null=True)
    wait = StringField(null=True)

    def __unicode__(self):
        return '%s %s %s' % (self.route, self.destination, self.wait)

    def json_dict(self):
        return {
            'route': self.route,
            'destination': self.destination,
            'wait': str(self.wait),
        }
