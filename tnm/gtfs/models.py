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

class Shape(DatasetModel):
    shape_id = StringField()
    line = models.LineStringField()
    objects = models.GeoManager() 
