$(function() {
    var mapElementName = 'map',
        initialLat = 38.89514125082739,
        initialLng = -77.03634738922119,
        getRadius = function()  { 
            return $('input:radio[name=radius-button]:checked').val(); 
        },
        map = Transit.addMap(
            'Leaflet', 
            mapElementName,
            { 
                'url': tnm_tile_server.url,
                'subdomains': tnm_tile_server.subdomains,
                'max_zoom': tnm_tile_server.max_zoom,
                'lat': initialLat, 
                'lng': initialLng, 
                'radius': getRadius() });

    map.addCallback({
        types: ['dblclick'],
        before: function(e) {
            map.center(e.latlng);
        }
    });

    map.addCallback({
        types: ['center'],
        apiCall: Transit.API.getNearby,
        extraParams: { 'radius_m': getRadius },
        before: function(e) {
            map.radius(e.latlng, getRadius());
            map.overlay('nearby');
            $.mobile.showPageLoadingMsg();
        },
        after: function(e, data) {
            map.radius(e.latlng, getRadius());
            $(window).resize();
            $.mobile.hidePageLoadingMsg();
            
            if (!data.coverage) {
                $('#home').simpledialog({
                    'mode': 'bool',
                    'prompt': 'Sorry, no coverage here.',
                    'subTitle': 'Transit Near Me is currently only available for the Washington, DC area.',
                    'useDialogForceFalse': true,
                    'cleanOnClose': true,
                    'buttons': {
                       'Take me there!': {
                            click: function() {
                                map.center({ 
                                    'lat': initialLat,
                                    'lng': initialLng
                                });
                            }
                        }
                    }
                });
            } else {
                map.radius(e.latlng, getRadius());
                map.overlay('nearby', data);
                $(window).resize();
                $.mobile.hidePageLoadingMsg();
                
                if (!data.stops.length) {
                    $('#home').simpledialog({
                        'mode': 'blank',
                        'forceInput': false,
                        'fullHTML': '<div id="no-content-notification" class="ui-simpledialog-notification"><p>No transit nearby.</p><p>Try another location or a larger search radius.</p></div>',
                        'useDialogForceFalse': true,
                        'cleanOnClose': true,
                        'animate': false,
                        'onCreated': function(e) {
                            setTimeout(function() { 
                                if ($('#home').data('simpledialog')) {
                                    $('#home').simpledialog('close');
                                }
                            }, 3000);
                        }
                    });
                }
            }
        }
    }); 

    var do_resize = function() {
        var viewport_height = window.innerHeight,
            header = $(".ui-header:visible"),
            content = $(".content:visible"),
	    footer = $(".ui-footer:visible");
        content.height(viewport_height - header.outerHeight() - footer.outerHeight());
	map.redraw();
    };

    $(window).bind("orientationchange", function() {
        scroll(0, 0);
        do_resize();
    });
    $(window).bind("resize pageshow", do_resize);
    
    $('#location-input').bind("blur", function() {
        scroll(0, 0);
    });

	
    $('#footer-form').bind("submit", function() {
        $.mobile.showPageLoadingMsg();
        url = 'http://where.yahooapis.com/geocode?q=' + escape($('#location-input').val()) + '&flags=J' + '&appId=' + tnm_geocoder_key;
        $.ajax({
            url: url,
            datatype: 'json',
            beforeSend: function(xhr){
				if (xhr.overrideMimeType)
				{
				  xhr.overrideMimeType("application/json");
				}
			  },
            success: function(data) {
                if (data.ResultSet) {
					if (!data.ResultSet.Error && data.ResultSet.Results) {
						if (data.ResultSet.Results[0].quality < 80) {
							$('#location-input').val($('#location-input').val() + ' (Approximate)');
						}
	                    map.center({
		                    lat: data.ResultSet.Results[0].latitude,
			                lng: data.ResultSet.Results[0].longitude
				        });
					}
				}
            }
        });

        $('#location-input').blur();
        return false;
    });

    var geolocate = function() {
        Transit.tryGeolocating(
            function(latlng) { map.center(latlng); },
            function(error) { map.center(); });
    }

    $('#home-button').bind("click", function() {
        geolocate();
        return false;
    });
    geolocate();
    
});
