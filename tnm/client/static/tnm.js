$(function() {
	var mapElementName = 'map',
		getRadius = function()  { 
			return $('input:radio[name=radius-button]:checked').val(); 
		},
		map = Transit.addMap(
			'Leaflet', 
			mapElementName,
			{ 
				'lat': 38.89706, 
				'lng': -77.07092, 
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
			map.overlay('nearby', data);
			$(window).resize();
			$.mobile.hidePageLoadingMsg();
		}
	});	
	
	$('#options').live('pagehide', function(e) {
		map.center();
	});

    var do_resize = function() {
		var viewport_height = window.innerHeight,
			header = $(".header:visible"),
			content = $(".content:visible");
		content.height(viewport_height - header.outerHeight());
    };

	$(window).bind("orientationchange", function() {
        scroll(0, 0);
        do_resize();
    });
    $(window).bind("resize pageshow", do_resize);
	
	Transit.tryGeolocating(
		function(latlng) { map.center(latlng); },
		function(error) { map.center(); });
});
