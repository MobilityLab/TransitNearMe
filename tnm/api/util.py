import gpolyencode
import json

from django.contrib.gis.geos import Point, LineString
from django.contrib.gis.measure import Distance
from sys import stdout

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Check if object exposes pre-computed json.
        if hasattr(obj, '_json'):
            _json = getattr(obj, '_json')
            if _json:
                return _json
            else:
                json_dict = getattr(obj, 'json_dict')
                if callable(json_dict):
                    return json_dict()

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

def enumerate_verbose(iterable, msg, stream=stdout):
    reported_pct = -1
    try:
        num = len(iterable)
    except TypeError:
        iterable_list = list(iterable)
        num = len(iterable_list)

    for i, item in enumerate(iterable):
        pct = 100 * i / num
        if pct > reported_pct:
            stream.write("\r%s...%s%%" % (msg, pct))
            stream.flush()
            reported_pct = pct

        yield item

    stream.write("\r%s...done.\n" % msg)
