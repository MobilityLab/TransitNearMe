from django.conf.urls.defaults import patterns, include, url
from django.contrib.gis import admin
from django.views.generic.simple import direct_to_template

admin.autodiscover()

urlpatterns = patterns('')

urlpatterns += patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += patterns('',
	(r'^transitnearme/$', direct_to_template, {'template': 'leaflet.html'}), 
	(r'^api/', include('api.urls')),
)
