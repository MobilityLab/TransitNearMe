import json
from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('',
    (r'^$', direct_to_template, {
        'template': 'client/leaflet.html',
        'extra_context': { 
            'tile_server': settings.TILE_SERVER,
			'geocoder_key': settings.TNM_GEOCODER_KEY
        }   
    }),
)
