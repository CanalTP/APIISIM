from apiisim.common import TransportModeEnum, StatusCodeEnum, SelfDriveModeEnum
from copy import deepcopy

datetime_pattern = '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$'
duration_pattern = 'P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?' \
                   '(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?' \
                   '(?:(?P<seconds>\d+)S)?)?'

ending_search_format = dict(type='object', properties={
    'RequestId': {'type': 'string'},
    'Status': {'enum': ['0', '1', '2']},
    'MaxComposedTripSearched': {'type': 'integer'},
    'ExistenceNotificationsSent': {'type': 'integer'},
    'NotificationsSent': {'type': 'integer'},
    'Runtime': {'type': 'string', 'pattern': duration_pattern},
}, required=['RequestId', 'Status', 'MaxComposedTripSearched',
             'ExistenceNotificationsSent', 'NotificationsSent', 'Runtime'])

starting_search_format = dict(type='object', properties={
    'RequestId': {'type': 'string'},
    'Status': {'enum': ['0', '1', '2']},
    'MaxComposedTripSearched': {'type': 'integer'},
}, required=['RequestId', 'MaxComposedTripSearched'])

error_format = dict(type='object', properties={
    'Field': {'type': 'string'},
    'Message': {'type': 'string'},
}, required=['Field', 'Message'])

plan_trip_response_format = dict(type='object', properties={
    'clientRequestId': {'type': 'string'},
    'Status': {'enum': ['0', '1', '2']},
    'errors': {'type': 'array',
               'items': [error_format]}
}, required=['clientRequestId', 'Status'])

location_structure_format = dict(type='object', properties={
    'Longitude': {'type': 'number'},
    'Latitude': {'type': 'number'},
}, required=['Longitude', 'Latitude'])

location_point_format = dict(type='object', properties={
    'PlaceTypeId': {'type': 'string'},
    'Position': location_structure_format,
})

trip_stop_place_format = dict(type='object', properties={
    'id': {'type': 'string'},
    'Position': location_structure_format,
    'Name': {'type': 'string'},
    'CityCode': {'type': 'string'},
    'CityName': {'type': 'string'},
    'POITypeName': {'type': 'string'},
    'TypeOfPlaceRef': {'type': 'string'},
}, required=['id', 'TypeOfPlaceRef'])

end_point_format = dict(type='object', properties={
    'TripStopPlace': trip_stop_place_format,
    'DateTime': {'type': 'string', 'pattern': datetime_pattern},
}, required=['TripStopPlace', 'DateTime'])

provider_format = dict(type='object', properties={
    'Name': {'type': 'string'},
    'Url': {'type': 'string'},
}, required=['Name'])

plan_trip_existence_notification_format = dict(type='object', properties={
    'RequestId': {'type': 'string'},
    'Status': {'enum': ['0', '1', '2']},
    'RuntimeDuration': {'type': 'string', 'pattern': duration_pattern},
    'ComposedTripId': {'type': 'string'},
    'DepartureTime': {'type': 'string', 'pattern': datetime_pattern},
    'ArrivalTime': {'type': 'string', 'pattern': datetime_pattern},
    'Duration': {'type': 'string', 'pattern': duration_pattern},
    'Departure': location_point_format,
    'Arrival': location_point_format,
    'providers': {'type': 'array',
                  'items': [provider_format]},
}, required=['RequestId', 'DepartureTime', 'ArrivalTime', 'ComposedTripId',
             'Duration', 'Departure', 'Arrival', 'providers'])

step_end_point_format = dict(type='object', properties={
    'TripStopPlace': trip_stop_place_format,
    'DateTime': {'type': 'string', 'pattern': datetime_pattern},
    'PassThrough': {'type': 'boolean'}
}, required=['TripStopPlace', 'DateTime'])

step_format = dict(type='object', properties={
    'id': {'type': 'string'},
    'Departure': step_end_point_format,
    'Arrival': step_end_point_format,
    'Duration': {'type': 'string', 'pattern': duration_pattern},
    'Distance': {'type': 'integer'},
}, required=['id', 'Departure', 'Arrival', 'Duration'])

pt_network_format = dict(type='object', properties={
    'id': {'type': 'string'},
    'Name': {'type': 'string'},
    'RegistrationNumber': {'type': 'string'},
}, required=['id', 'Name'])

line_format = dict(type='object', properties={
    'id': {'type': 'string'},
    'Name': {'type': 'string'},
    'Number': {'type': 'string'},
    'PublishedName': {'type': 'string'},
    'RegistrationNumber': {'type': 'string'},
}, required=['id', 'Name'])

pt_ride_format = dict(type='object', properties={
    'PublicTransportMode': {'enum': [x for x in TransportModeEnum.values()]},
    'Departure': end_point_format,
    'Arrival': end_point_format,
    'Duration': {'type': 'string', 'pattern': duration_pattern},
    'Distance': {'type': 'integer'},
    'PTNetwork': pt_network_format,
    'Line': line_format,
    'StopHeadSign': {'type': 'string'},
    'steps': {'type': 'array',
              'items': [step_format]},
}, required=['PublicTransportMode', 'Departure',
             'Arrival', 'Duration', 'steps'])

leg_format = dict(type='object', properties={
    'SelfDriveMode': {'enum': [x for x in SelfDriveModeEnum.values()]},
    'Departure': end_point_format,
    'Arrival': end_point_format,
    'Duration': {'type': 'string', 'pattern': duration_pattern},
}, required=['SelfDriveMode', 'Departure', 'Arrival', 'Duration'])

section_format = dict(type='object', properties={
    'PartialTripId': {'type': 'string'},
    'PTRide': pt_ride_format,
    'Leg': leg_format,
}, required=['PartialTripId'])

partial_trip_format = dict(type='object', properties={
    'id': {'type': 'string'},
    'Provider': provider_format,
    'Distance': {'type': 'integer'},
    'Departure': end_point_format,
    'Arrival': end_point_format,
    'Duration': {'type': 'string', 'pattern': duration_pattern},
}, required=['id', 'Departure', 'Arrival', 'Duration', 'Provider'])

trip_format = dict(type='object', properties={
    'id': {'type': 'string'},
    'Departure': end_point_format,
    'Arrival': end_point_format,
    'Duration': {'type': 'string', 'pattern': duration_pattern},
    'Distance': {'type': 'integer'},
    'InterchangeNumber': {'type': 'integer'},
    'sections': {'type': 'array',
                 'items': [section_format]},
}, required=['Departure', 'Arrival', 'Duration', 'sections'])

composed_trip_format = deepcopy(trip_format)
composed_trip_format['properties']['partialTrips'] = {'type': 'array',
                                                      'items': [partial_trip_format]}
composed_trip_format['required'].append('partialTrips')

plan_trip_notification_response_format = dict(type='object', properties={
    'RequestId': {'type': 'string'},
    'Status': {'enum': ['0', '1', '2']},
    'RuntimeDuration': {'type': 'string', 'pattern': duration_pattern},
    'ComposedTrip': composed_trip_format,
}, required=['RequestId'])

status_format = dict(type='object', properties={
    'Code': {'enum': [x for x in StatusCodeEnum.values()]},
    'RuntimeDuration': {'type': 'string'},
}, required=['Code'])

summed_up_trip_format = dict(type='object', properties={
    'Departure': end_point_format,
    'Arrival': end_point_format,
    'InterchangeCount': {'type': 'integer'},
    'InterchangeDuration': {'type': 'integer'},

}, required=['Departure', 'Arrival', 'InterchangeCount',
             'InterchangeDuration'])

summed_up_itineraries_response_format = dict(type='object', properties={
    'RequestId': {'type': 'string'},
    'Status': status_format,
    'summedUpTrips': {'type': 'array',
                      'items': [summed_up_trip_format]},
}, required=['RequestId', 'Status'])

itinerary_response_format = dict(type='object', properties={
    'RequestId': {'type': 'string'},
    'Status': status_format,
    'DetailedTrip': trip_format,
}, required=['RequestId', 'Status'])
