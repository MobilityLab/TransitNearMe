from django.conf.urls.defaults import patterns, include, url
from api.views import *

urlpatterns = patterns('api.views',
	url(r'^nearby$', nearby, name='nearby'),
)
