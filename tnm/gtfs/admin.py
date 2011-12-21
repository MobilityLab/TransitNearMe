from django.contrib.gis import admin
from gtfs.models import *

admin.site.register(Agency)
admin.site.register(Stop, admin.OSMGeoAdmin)
admin.site.register(Route)

class ShapeAdmin(admin.OSMGeoAdmin):
    list_display = ['shape_ids']

admin.site.register(Shape, ShapeAdmin)

class PatternStopInline(admin.TabularInline):
    model = PatternStop

class PatternAdmin(admin.ModelAdmin):
    list_filter = ['route__agency', 'route']
    inlines = [PatternStopInline]

admin.site.register(Pattern, PatternAdmin)
