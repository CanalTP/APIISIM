from flask_restful import fields, marshal as flask_marshal
import datetime

DATE_FORMAT="%Y-%m-%dT%H:%M:%S"


"""
    Custom DateTime marshaller that converts DateTime object to a DATE_FORMAT 
    formatted string.
"""
class _DateTime(fields.DateTime):
    def format(self, value):
        try:
            return datetime.datetime.strftime(value, DATE_FORMAT)
        except AttributeError as ae:
            raise fields.MarshallingException(ae)

"""
    Ignore null elements when marshalling.
    Note that it only works when using our customized flask library. When using stock
    flask library, this is equivalent to fields.Nested (null elements will 
    therefore still be there after marshalling).
"""
class NonNullNested(fields.Nested):

    def __init__(self, *args, **kwargs):
        super(NonNullNested, self).__init__(*args, **kwargs)
        self.display_null = False

"""
    Ignore null elements when marshalling.
    Note that it only works when using our customized flask library. When using stock
    flask library, this is equivalent to fields.List (null elements will 
    therefore still be there after marshalling).
"""
class NonNullList(fields.List):

    def __init__(self, *args, **kwargs):
        super(NonNullList, self).__init__(*args, **kwargs)
        self.display_empty = False


# Ignore None attributes
def marshal(obj, fields):
    ret = flask_marshal(obj, fields)
    items = ret.iteritems()
    for k, v in items:
        if v is None:
            del ret[k]
    return ret


stop_fields = {'code': fields.String, 'name': fields.String,
               'lat': fields.Float, 'long': fields.Float}

location_structure_type = {
    'Latitude' : fields.Float,
    'Longitude' : fields.Float
}

location_context_type = {
    'PlaceTypeId' : fields.String,
    'Position' : NonNullNested(location_structure_type, allow_null=True),
    'AccessTime' : fields.Integer,
}

self_drive_condition_type = {
    'TripPart' : fields.String,
    'SelfDriveMode' : fields.String,
}

multi_departures_type = {
    'Departure' : NonNullList(NonNullNested(location_context_type)),
    'Arrival' : NonNullNested(location_context_type),
}

multi_arrivals_type = {
    'Departure' : NonNullNested(location_context_type),
    'Arrival' : NonNullList(NonNullNested(location_context_type)),
}

itinerary_request_type = {
    'id' : fields.String,
    'multiDepartures' : NonNullNested(multi_departures_type, allow_null=True),
    'multiArrivals' : NonNullNested(multi_arrivals_type, allow_null=True),
    'DepartureTime' : _DateTime,
    'ArrivalTime' : _DateTime,
    'Algorithm' : fields.String,
    'modes' : NonNullList(fields.String),
    'selfDriveConditions' : NonNullList(NonNullNested(self_drive_condition_type)),
    # 'selfDriveConditions' : fields.List(fields.Nested(self_drive_condition_type, allow_null=True)),
    'AccessibilityConstraint' : fields.Boolean,
    'Language' : fields.String,
}

summed_up_itineraries_request_type = {
    'id' : fields.String,
    'departures' : NonNullList(NonNullNested(location_context_type)),
    'arrivals' : NonNullList(NonNullNested(location_context_type)),
    'DepartureTime' : _DateTime,
    'ArrivalTime' : _DateTime,
    'Algorithm' : fields.String,
    'modes' : NonNullList(fields.String),
    'selfDriveConditions' : NonNullList(NonNullNested(self_drive_condition_type)),
    'AccessibilityConstraint' : fields.Boolean,
    'Language' : fields.String,
    'options' : NonNullList(fields.String),
}

location_point_type = {
    'PlaceTypeId' : fields.String,
    'Position' : NonNullNested(location_structure_type, allow_null=True),
}

place_type = {
    'id' : fields.String,
    'Position' : fields.Nested(location_structure_type, allow_null=True),
    'Name' : fields.String,
    'CityCode' : fields.String,
    'CityName' : fields.String,
    'TypeOfPlaceRef' : fields.String,
}

trip_stop_place_type = place_type.copy()
# Parent attribute is currently not implemented and is therefore
# always empty, so ignore it for now.
# trip_stop_place_type['Parent'] = NonNullNested(place_type)

end_point_type = {
    'TripStopPlace' : fields.Nested(trip_stop_place_type),
    'DateTime' : _DateTime
}

provider_type = {
    'Name' : fields.String,
    'Url' : fields.String,
}

plan_trip_existence_notification_response_type = {
    'RequestId' : fields.String,
    'DepartureTime' : _DateTime,
    'ArrivalTime' : _DateTime,
    'Duration' : fields.String,
    'Departure' : NonNullNested(location_point_type),
    'Arrival' : NonNullNested(location_point_type),
    'providers' : NonNullList(NonNullNested(provider_type)),
}

plan_trip_notification_status_type = {
    'PlanTripNotificationStatusCode' : fields.String,
    'isLastNotification' : fields.Boolean,
    'Comment' : fields.String,
    'NotificationIndex' : fields.Integer,
    'NotificationCount' : fields.Integer,
    'RuntimeDuration' : fields.Integer,
}

step_end_point_type = {
    'TripStopPlace' : fields.Nested(trip_stop_place_type),
    'DateTime' : _DateTime,
    'PassThrough' : fields.String
}

step_type = {
    'id' : fields.String,
    'Departure' : fields.Nested(step_end_point_type),
    'Arrival' : fields.Nested(step_end_point_type),
    'Duration' : fields.Integer
}

pt_ride_type = {
    'ptNetworkRef' : fields.String,
    'lineRef' : fields.String,
    'PublicTransportMode' : fields.String,
    'Departure' :  fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'Duration' : fields.Integer,
    'Distance' : fields.Integer,
    'steps' : NonNullList(NonNullNested(step_type))
}

leg_type = {
    'SelfDriveMode' : fields.String,
    'Departure' : fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'Duration' : fields.Integer
}

section_type = {
    'PartialTripId' : fields.String,
    'PTRide' : fields.Nested(pt_ride_type, allow_null=True),
    'Leg' : fields.Nested(leg_type, allow_null=True)
}

trip_type = {
    'id' : fields.Integer,
    'Departure' : fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'Duration' : fields.Integer,
    'Distance' : fields.Integer,
    'InterchangeNumber' : fields.Integer,
    'sections' : NonNullList(NonNullNested(section_type))
}

partial_trip_type = {
    'id' : fields.String,
    'Provider' : NonNullNested(provider_type),
    'Distance' : fields.Integer,
    'Departure' : fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'Duration' : fields.Integer,
}

composed_trip_type = {
    'id' : fields.String,
    'Departure' : fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'Duration' : fields.Integer,
    'Distance' : fields.Integer,
    'InterchangeNumber' : fields.Integer,
    'sections' : NonNullList(NonNullNested(section_type)),
    'partialTrips' : NonNullList(NonNullNested(partial_trip_type)),
}

plan_trip_notification_response_type = {
    'RequestId' : fields.String,
    'PlanTripNotificationStatus' : NonNullNested(plan_trip_notification_status_type),
    'ComposedTrip' : NonNullList(NonNullNested(composed_trip_type)),
}

plan_trip_cancellation_response_type = {
    'RequestId' : fields.String,
}

plan_trip_cancellation_request_type = {
    'RequestId' : fields.String,
}

status_type = {
    'Code' : fields.String,
    'RuntimeDuration' : fields.Float
}

itinerary_response_type = {
    'RequestId' : fields.String,
    'Status' : fields.Nested(status_type),
    'DetailedTrip' : fields.Nested(trip_type, allow_null=True)
}

summed_up_trip_type = {
    'Departure' : fields.Nested(end_point_type),
    'Arrival' : fields.Nested(end_point_type),
    'InterchangeCount' : fields.Integer,
    'InterchangeDuration' : fields.Integer
}

summed_up_itineraries_response_type = {
    'RequestId' : fields.String,
    'Status' : fields.Nested(status_type),
    'summedUpTrips' : NonNullList(NonNullNested(summed_up_trip_type))
}

plan_trip_request_type = {
    'id' : fields.String,
    'Departure' : NonNullNested(location_context_type),
    'Arrival' : NonNullNested(location_context_type),
    'DepartureTime' : _DateTime,
    'ArrivalTime' : _DateTime,
    'MaxTrips' : fields.Integer,
    'Algorithm' : fields.String,
    'modes' : NonNullList(fields.String),
    'selfDriveConditions' : NonNullList(NonNullNested(self_drive_condition_type)),
    'AccessibilityConstraint' : fields.Boolean,
    'Language' : fields.String,
}

error_type = {
    'Field' : fields.String,
    'Message' : fields.String,
}

plan_trip_response_type = {
    'RequestId' : fields.String,
    'Status' : fields.String,
    'errors' : NonNullList(NonNullNested(error_type)),
}

ending_search_type = {
    'RequestId' : fields.String,
    'Status' : fields.String,
    'MaxComposedTripSearched' : fields.Integer,
    'ExistenceNotificationsSent' : fields.Integer,
    'NotificationsSent' : fields.Integer,
    'Runtime' : fields.Integer,
}


starting_search_type = {
    'RequestId' : fields.String,
    'Status' : fields.String,
    'MaxComposedTripSearched' : fields.Integer,
}
