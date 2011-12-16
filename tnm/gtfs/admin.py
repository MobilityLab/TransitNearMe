from django.contrib.gis import admin
from gtfs.models import Shape

admin.site.register(Shape, admin.OSMGeoAdmin)
