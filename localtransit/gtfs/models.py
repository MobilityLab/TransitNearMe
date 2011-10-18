from django.contrib.gis.db import models
from stringfield import StringField

class Agency(models.Model):
	class Meta:
		db_table = 'agency'

	agency_id = StringField(null=True)
	agency_name = StringField()
	agency_url = StringField()
	agency_timezone = StringField()
	agency_lang = StringField(null=True)
	agency_phone = StringField(null=True)
	agency_fare_url = StringField(null=True)

	def __unicode__(self):
		return self.agency_name

class Calendar(models.Model):
	class Meta:
		db_table = 'calendar'

	service_id = StringField(primary_key=True)
	monday = models.BooleanField()
	tuesday = models.BooleanField()
	wednesday = models.BooleanField()
	thursday = models.BooleanField()
	friday = models.BooleanField()
	saturday = models.BooleanField()
	sunday = models.BooleanField()
	start_date = models.DateField()
	end_date = models.DateField()

class CalendarDate(models.Model):
	class Meta:
		db_table = 'calendar_dates'
		unique_together = ('service_id', 'date',)

	service_id = StringField(primary_key=True)
	date = models.DateField()
	exception_type = models.IntegerField()

class FareAttribute(models.Model):
	class Meta:
		db_table = 'fare_attributes'

	fare_id = StringField(primary_key=True)
	price = models.FloatField() # should be numeric(10,2)
	currency_type = StringField()
	payment_method = models.IntegerField()
	transfers = models.IntegerField(null=True)
	transfer_duration = models.IntegerField(null=True)

class FareRule(models.Model):
	class Meta:
		db_table = 'fare_rules'

	fare_id = models.ForeignKey(FareAttribute)
	route_id = StringField(null=True)
	origin_id = StringField(null=True)
	destination_id = StringField(null=True)
	contains_id = StringField(null=True)
	service_id = StringField(null=True)

class FeedInfo(models.Model):
	class Meta:
		db_table = 'feed_info'

	feed_publisher_name = StringField(primary_key=True)
	feed_publisher_url = StringField()
	feed_lang = StringField()
	feed_start_date = models.DateField(null=True)
	feed_end_date = models.DateField(null=True)
	feed_version = StringField(null=True)

class UniversalCalendar(models.Model):
	class Meta:
		db_table = 'universal_calendar'
		unique_together = ('service_id', 'date',)

	service_id = StringField(primary_key=True)
	date = models.DateField()

