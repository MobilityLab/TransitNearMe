import gpolyencode
import json

from django.contrib.gis.geos import Point, LineString
from django.contrib.gis.measure import Distance

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Check if object exposes pre-computed json.
        if hasattr(obj, '_json'):
            _json = getattr(obj, '_json')
            if _json:
                return _json

        # Handle special classes.
        if isinstance(obj, Point):
            return {'lng': obj.x, 'lat': obj.y}
        if isinstance(obj, LineString):
            encoder = gpolyencode.GPolyEncoder()
            return encoder.encode(obj.coords)    
        if isinstance(obj, Distance):
            return obj.m
 
        # Try iterating.
        try:
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(obj)

        return json.JSONEncoder.default(self, obj)

