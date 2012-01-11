from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from django.contrib.gis import admin
from django.utils.translation import ugettext_lazy as _
from stringfield import StringField

from api.models import *
from transitapis.models import Stop as API_Stop

# Remove default User, Group, and Site models
admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.unregister(Site)

# Useful interface options
formfield_overrides = {
    StringField: {'widget': forms.TextInput(attrs={'size': 100})},
}

class NoChangeAdmin(admin.ModelAdmin):
    actions = None
    formfield_overrides = formfield_overrides

    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
admin.site.register(Agency, NoChangeAdmin)

class RouteAdmin(NoChangeAdmin):
    list_filter = ['agency']

admin.site.register(Route, RouteAdmin)

class GeoNoChangeAdmin(admin.OSMGeoAdmin):
    actions = None
    formfield_overrides = formfield_overrides

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(RouteSegment, GeoNoChangeAdmin)

class RouteSegmentInline(admin.StackedInline):
    model = RouteSegment

class ServiceFromStopAdmin(GeoNoChangeAdmin):
    list_filter = ['route__agency', 'route']
    readonly_fields = ['segments']

admin.site.register(ServiceFromStop, ServiceFromStopAdmin)

# Stop model
class StopAdminForm(forms.ModelForm):
    latitude = forms.FloatField(required=False)
    longitude = forms.FloatField(required=False)

    class Meta:
        model = Stop

    def __init__(self, *args, **kwargs):
        super(StopAdminForm, self).__init__(*args, **kwargs)

        if kwargs.has_key('instance'):
            instance = kwargs['instance']
            self.initial['latitude'] = instance.latitude
            self.initial['longitude'] = instance.longitude

    def save(self, commit=True):
        model = super(StopAdminForm, self).save(commit=False)

        model.latitude = self.cleaned_data['latitude']
        model.longitude = self.cleaned_data['longitude']

        if commit:
            model.save()

        return model

class StopAdmin(admin.OSMGeoAdmin):
    form = StopAdminForm
    actions = None
    formfield_overrides = formfield_overrides
    list_filter = ['services_leaving__route__agency']   
 
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(Stop, StopAdmin)
