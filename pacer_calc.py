import math
import datetime
import numpy as np
import pandas as pd
import gpxpy
import gpxpy.gpx

def distance(lat1, lon1, lat2, lon2):
    earthRadius = 6371000

    dLat = math.radians(lat2-lat1)
    dLon = math.radians(lon2-lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    a = math.sin(dLat/2) * math.sin(dLat/2) + math.sin(dLon/2) * math.sin(dLon/2) * math.cos(lat1) * math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
  
    return earthRadius * c

def gain(elevation_delta):
    if elevation_delta > 0:
        return elevation_delta
    else:
        return 0

def time_delta(t1, t0):
    if t0 is pd.NaT:
        return int(0)
    else:
        return datetime.timedelta.total_seconds(t1-t0)

def distance_to_segment(value):
    if math.isnan(value):
        return int(0)
    else:
        return int(value/100)

def load_reference_data(gpx_file):
    gpx = gpxpy.parse(gpx_file)

    cols = [ 'lat', 'lon', 'elevation', 'time' ]
    idx = []
    rows = []

    row = 0
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                idx.append(row)
                rows.append([point.latitude, point.longitude, point.elevation, point.time])
                row = row + 1
                
    reference_data = pd.DataFrame(data=rows, index=idx, columns=cols)

    reference_data['elevation_delta'] = reference_data.elevation.diff().shift(0)

    reference_data['time_prev'] = reference_data.time.shift(+1)
    reference_data['time_delta'] = reference_data.apply(
        lambda row: time_delta(row['time'], row['time_prev']), axis=1)
    del reference_data['time']
    del reference_data['time_prev']


    reference_data['lat_prev'] = reference_data.lat.shift(+1)
    reference_data['lon_prev'] = reference_data.lon.shift(+1)
    reference_data['distance_delta'] = reference_data.apply(
        lambda row: distance(row['lat'],row['lon'], row['lat_prev'],row['lon_prev']), axis=1)
    del reference_data['lat_prev']
    del reference_data['lon_prev']

    reference_data['distance_sum'] = reference_data['distance_delta'].cumsum(axis = 0)
    reference_data['distance_segment'] = reference_data.apply(
        lambda row: distance_to_segment(row['distance_sum']), axis=1)

    grouped_reference_data = reference_data.groupby('distance_segment').agg(
    {
        'elevation': ['mean'],
        'elevation_delta': ['sum'],
        'distance_delta': ['sum'], 
        'time_delta': ['sum']})
    grouped_reference_data['pace_segment'] = 16.7/(
        grouped_reference_data[('distance_delta','sum')]/grouped_reference_data[('time_delta','sum')])
    grouped_reference_data['distance_sum'] = grouped_reference_data['distance_delta'].cumsum(axis = 0)

    return grouped_reference_data

def load_target_data(target_gpx_file):
    target_gpx = gpxpy.parse(target_gpx_file)

    cols = [ 'lat', 'lon', 'elevation' ]
    idx = []
    rows = []

    row = 0
    for track in target_gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                idx.append(row)
                rows.append([point.latitude, point.longitude, point.elevation])
                row = row + 1

    target_data = pd.DataFrame(data=rows, index=idx, columns=cols)

    target_data['elevation_delta'] = target_data.elevation.diff().shift(0)

    target_data['lat_prev'] = target_data.lat.shift(+1)
    target_data['lon_prev'] = target_data.lon.shift(+1)
    target_data['distance_delta'] = target_data.apply(
        lambda row: distance(row['lat'],row['lon'], row['lat_prev'],row['lon_prev']), axis=1)
    del target_data['lat_prev']
    del target_data['lon_prev']

    target_data['distance_sum'] = target_data['distance_delta'].cumsum(axis = 0)
    target_data['distance_segment'] = target_data.apply(
        lambda row: distance_to_segment(row['distance_sum']), axis=1)

    grouped_target_data = target_data.groupby('distance_segment').agg(
        {
            'elevation': ['mean'],
            'elevation_delta': ['sum'],
            'distance_delta': ['sum']})
    grouped_target_data['distance_sum'] = grouped_target_data['distance_delta'].cumsum(axis = 0)
    grouped_target_data['elevation_sum'] = grouped_target_data['elevation_delta'].cumsum(axis = 0)

    return grouped_target_data

def evaluate_model_parameters(grouped_reference_data):
    sorted_grouped_reference_data = grouped_reference_data.sort_values(by=('elevation_delta','sum'))
    x_arr = sorted_grouped_reference_data[('elevation_delta','sum')].values
    y_arr = sorted_grouped_reference_data['pace_segment'].values

    # Step 1: Prepare arrays
    x_all_arr = []
    y_all_arr = []
    x_up_arr = []
    y_up_arr = []
    x_down_arr = []
    y_down_arr = []

    for i in range(0, len(x_arr)):
        if y_arr[i] < 20:
            x_all_arr.append(x_arr[i])
            y_all_arr.append(y_arr[i])
            if x_arr[i] > 0:
                x_up_arr.append(x_arr[i])
                y_up_arr.append(y_arr[i])
            else:
                x_down_arr.append(x_arr[i])
                y_down_arr.append(y_arr[i])

    # Step 2: Prepare model parameters
    model_parameters = {}

    # 2.1: Manual
    model_parameters['uphill_penalty_per_m']=6/20
    model_parameters['downhill_penalty_per_m']=3/20

    # 2.2: Parabolic (general, downhill only)
    (
        model_parameters['a_para'],
        model_parameters['b_para'],
        model_parameters['c_para']) = np.polyfit(x_all_arr, y_all_arr, 2)
    (
        model_parameters['a_para_down'],
        model_parameters['b_para_down'],
        model_parameters['c_para_down']) = np.polyfit(x_down_arr, y_down_arr, 2)
    
    # 2.3: Linear (uphill, downhill)
    (
        model_parameters['a_lin_up'],
        model_parameters['b_lin_up']) = np.polyfit(x_up_arr, y_up_arr, 1)
    (
        model_parameters['a_lin_down'],
        model_parameters['b_lin_down']) = np.polyfit(x_down_arr, y_down_arr, 1)

    return model_parameters

def predict_pace_raw(model_parameters, elevation, base_pace, model):

    # Step 3: Predict pace
    if model=='manual':
        if elevation > 0:
            return base_pace+elevation*model_parameters['uphill_penalty_per_m']
        else:
            return base_pace+abs(elevation)*model_parameters['downhill_penalty_per_m']

    elif model=='parabolic':
        return model_parameters['a_para']*elevation**2+model_parameters['b_para']*elevation+model_parameters['c_para']
    
    elif model=='linear':
        if elevation >= 0:
            return model_parameters['a_lin_up']*elevation+model_parameters['b_lin_up']
        else:
            return model_parameters['a_lin_down']*elevation+model_parameters['b_lin_down']
    
    elif model=='hybrid':
        if elevation > 0:
            return model_parameters['a_lin_up']*elevation+model_parameters['b_lin_up']
        else:
            return model_parameters['a_para_down']*elevation**2+model_parameters['b_para_down']*elevation+model_parameters['c_para_down']
        
def predict_pace(model_parameters, elevation, base_pace, model, min_pace=19):
    pace = predict_pace_raw(model_parameters, elevation, base_pace, model)
    if pace > min_pace:
        return min_pace
    else:
        return pace
