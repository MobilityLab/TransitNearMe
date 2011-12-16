from django.conf.urls.defaults import patterns, include, url
from django.contrib.gis import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^favicon\.ico$', 'django.views.generic.simple.redirect_to', {'url': '/static/images/favicon.ico'}),
)

urlpatterns += patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += patterns('',
	(r'^', include('client.urls')),
	(r'^api/', include('api.urls')),
    (r'^transitapis/', include('transitapis.urls')),
)
