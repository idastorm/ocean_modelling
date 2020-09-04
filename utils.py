from scipy.io import loadmat, savemat
import datetime
import numpy as np
import json
from geopy import distance

class Vessel:

        def __init__(self, x=None, y=None, craft=None, trajectory = None):

            self.craft = craft
            self.x = x
            self.y = y
            self.trajectory = trajectory if trajectory is not None else [[self.x.tolist()[0], self.y.tolist()[0]]]

        def update_position(self, x, y):
            
            self.x = x
            self.y = y

            self.trajectory.append([x.tolist()[0], y.tolist()[0]])


def dist2vessels(PX, PY, lon_0, lat_0, start_date='1979-01-01', limit_date='1980-01-01', day_frequency=5):

    limit_date  = datetime.date.fromisoformat(limit_date)
    launch_date = datetime.date.fromisoformat(start_date)
    launch_date = datetime.date.fromisoformat(start_date)
    launch_day_delta = datetime.timedelta(days=day_frequency)

    results = {}
    for i in range(PX.shape[1]):

        vessels = []

        for j in range(PX.shape[2]):
            x = PX[:, i, j]
            y = PY[:, i, j]

            x, y = relative_to_lon_lat(x, y, lon_0, lat_0)
            trajectory = np.vstack((x, y)).T.tolist()

            vessels.append(Vessel(trajectory=trajectory))

        results[launch_date.strftime("%Y-%m-%d")] = vessels
        
        launch_date += launch_day_delta

        if launch_date >= limit_date:
            break

    return results


def simulate_vessel_trajectory(vessel, day, timesteps, dt, lon_0, lat_0, currents, winds):

    current_in_x = currents[0]
    current_in_y = currents[1]
    wind_in_x    = winds[0]
    wind_in_y    = winds[1]

    x = vessel.x
    y = vessel.y
    # x = vessel[0][0]
    # y = vessel[0][1]

    longitude = x
    latitude  = y

    for t in np.arange(timesteps):
        
        #longitude, latitude = relative_to_lon_lat(x, y, lon[0], lat[0])

        # longitude = x
        # latitude  = y
        # longitude = y
        # latitude  = x

        # v_x_current = current_in_x((day+t, longitude, latitude))
        # v_y_current = current_in_y((day+t, longitude, latitude))
    
        v_x_current = current_in_x((latitude, longitude))
        v_y_current = current_in_y((latitude, longitude))

        # Test if we have reached land
        if np.isnan(v_x_current) or np.isnan(v_y_current):
            break
                
        # If we have not reached land, get the wind velocity
        # v_x_wind = wind_in_x((day+t, longitude, latitude))
        # v_y_wind = wind_in_y((day+t, longitude, latitude))                

        v_x_wind = wind_in_x((latitude, longitude))
        v_y_wind = wind_in_y((latitude, longitude))  
        
        # print(v_x_current, v_y_current)
        # print(v_x_wind, v_y_wind)
        # Get displacement due to drift
        dx, dy = USCG_drift(np.array([v_x_wind, v_y_wind]),
                            np.array([v_x_current, v_y_current]), 
                            dt, 
                            vessel.craft
                            )

        # Get new position
        # y, x = distance.distance((lon_0, lat_0), (latitude, longitude)).km
        # print(dx, dy)
        old_lon = longitude
        old_lat = latitude
        longitude, latitude = lon_lat_from_displacement(dx, dy, longitude, latitude)

        print(abs(old_lon-longitude), abs(old_lat-latitude))
        # x += dx #+ noise_x
        # y += dy #+ noise_y

        # Update the vessel position and save
        vessel.update_position(longitude, latitude)
        # vessel.append([x, y])

    return vessel

def lon_lat_from_displacement(dx, dy, longitude, latitude):

    r_earth = 6371 # km

    new_latitude  = latitude  + (dy / r_earth) * (180 / np.pi);
    new_longitude = longitude + (dx / r_earth) * (180 / np.pi) / np.cos(latitude * np.pi/180);

    #print(new_longitude, new_latitude)

    return new_longitude, new_latitude


def bearing_from_displacement(x, v):

    return np.arccos(np.dot(np.cross(x, v), np.cross(x, v)) / (np.linalg.norm(np.cross()) * np.linalg.norm(dy)))

def relative_to_lon_lat(X, Y, lon_0, lat_0):


    lat = Y/(np.pi*6371)*180+lat_0
    lon = X/(np.pi*6371*np.cos(np.radians(lat)))*180+lon_0

    return lon, lat

def lon_lat_to_relative(lon, lat, lon_0, lat_0):
    
    Y = (lat - lat_0)*(np.pi*6371)/180
    X = (lon - lon_0)*(np.pi*6371*np.cos(np.radians(lat)))/180

    return X, Y


def get_bbox_mask(longitude, latitude, bbox):

    lon_min = bbox[0]
    lon_max = bbox[2]

    lat_min = bbox[1]
    lat_max = bbox[3]

    local_lon = (longitude > lon_min) & (longitude < lon_max)
    local_lat = (latitude > lat_min) & (latitude < lat_max)

    return local_lon, local_lat 


def in_bounding_box(x, longitude, latitude, bbox):
    
    lon_mask, lat_mask = get_bbox_mask(longitude, latitude, bbox)

    return x[lat_mask][:, lon_mask]

def get_departure_points(mask, longitude, latitude, offset=-1):

    mask[:,-1] = np.nan

    lon_coords = np.argmax(mask, axis=1) 

    lon_points = longitude[lon_coords]+offset
    lat_points = latitude

    return np.vstack((lon_points, lat_points)).T

def save_to_GeoJSON(data, filename):

    format_dict = {"type": "FeatureCollection",
                   "features": []}

    for date_key, vessels in data.items():
        # print(date_key, vessels)

        for vessel in vessels:

            d = {"type": "Feature", 
                "geometry": {
                    "type": "LineString",
                    "coordinates": vessel.trajectory
                },
                "properties": {
                    "date": date_key,
                    "number_of_days": len(vessel.trajectory)
                }}

            format_dict["features"].append(d)

    with open(filename, 'w') as file:
        json.dump(format_dict, file, indent=4)



# def average_velocity(U, V, X_i, Y_i):

#     U_avg = np.nanmean(U[X_i, Y_i])
#     V_avg = np.nanmean(V[X_i, Y_i])

#     return U_avg, V_avg




# def wind_and_current_indices(x, y, X, Y, Sx, Sy, overlap):

#     Y_i = indices_within_distance(y, Y[:,0], max_distance=overlap*Sy)

#     if len(Y_i) == 1:
#         X_i = indices_within_distance(x, X[Y_i, :], max_distance=overlap*Sx)

#     else: 
#         closest_indices_subset  = get_search_radius_indices(y, Y[Y_i,0])
#         closest_indices         = Y_i[closest_indices_subset]

#         X_i = indices_within_distance(x, X[closest_indices, :], max_distance=overlap*Sx)

#     return X_i, Y_i
     

# def get_search_radius(y, distance, Dx, Dy, max_distance):

#     # Get all available indices from surrouding bins
#     available_indices = get_available_position_indices(y, distance, max_distance)

#     # Check if there are no available indices
#     # if np.isnan(available_indices).all():
#     if len(available_indices) != 0:
#         # If there is only one index, we choose that one
#         if len(available_indices) == 1:
            
#             Sx, Sy = Dx[available_indices], Dy[available_indices]
        
#         # Otherwise we take the closest positions
#         else:
            
#             closest_indices_subset  = get_search_radius_indices(y, distance[available_indices])
#             closest_indices         = available_indices[closest_indices_subset]

#             Sx, Sy = np.array([Dx[closest_indices]]), np.array([Dy[closest_indices]])

#         return Sx, Sy
    
#     else:
#         return [], []

# def get_search_radius_indices(y, distance):
    
#     # Calculate the distance between all points
#     diff = np.abs(distance - y)

#     # Return the closest one
#     indices = np.argmin(diff)

#     return indices


# def indices_within_distance(x, distance, max_distance):
#     indices = np.where(np.logical_and(distance <= (x + max_distance), 
#                                       distance >= (x - max_distance)).flatten())[0]

#     return indices



# def get_available_position_indices(y, distance, max_distance):

#     #max_distance = 1.1 * MDy / 2

#     if not np.isnan(y):
#         available_indices = indices_within_distance(y, distance, max_distance)
#     else:
#         available_indices = np.nan

#     return available_indices


# def pad_borders(x, pad_value):

#     x[:,[0,-1]] = x[[0,-1],:] = pad_value

#     return x

def preprocess_mat(x):
    return np.flip(np.moveaxis(x, -1, 0), axis=1)


def load_current_data(year: int):

    # currents
    iCa_cU_D_1 = loadmat('iCa_cU_D_' + str(year))['iCa_cU_D_' + str(year)]
    iCa_cU_D_2 = loadmat('iCa_cU_D_' + str(year + 1))['iCa_cU_D_' + str(year + 1)]

    iCa_cV_D_1 = loadmat('iCa_cV_D_' + str(year))['iCa_cV_D_' + str(year)]
    iCa_cV_D_2 = loadmat('iCa_cV_D_' + str(year + 1))['iCa_cV_D_' + str(year + 1)]

    # the line below joins two years
    U2y = np.concatenate((iCa_cU_D_1, iCa_cU_D_2), axis=2)
    V2y = np.concatenate((iCa_cV_D_1, iCa_cV_D_2), axis=2)

    # U2y = np.transpose(U2y, axes=(1,0,2))
    # V2y = np.transpose(V2y, axes=(1,0,2))

    U2y = preprocess_mat(U2y)
    V2y = preprocess_mat(V2y)

    return U2y, V2y

def load_wind_data(year: int):

    # winds
    iCa_wU_D_1 = loadmat('iCa_wU_D_' + str(year))['iCa_wU_D_' + str(year)]
    iCa_wU_D_2 = loadmat('iCa_wU_D_' + str(year + 1))['iCa_wU_D_' + str(year + 1)]

    iCa_wV_D_1 = loadmat('iCa_wV_D_' + str(year))['iCa_wV_D_' + str(year)]
    iCa_wV_D_2 = loadmat('iCa_wV_D_' + str(year + 1))['iCa_wV_D_' + str(year + 1)]

    # the line below joins two years
    wU2y = np.concatenate((iCa_wU_D_1, iCa_wU_D_2), axis=2)
    wV2y = np.concatenate((iCa_wV_D_1, iCa_wV_D_2), axis=2)

    # wU2y = np.transpose(wU2y, axes=(1,0,2))
    # wV2y = np.transpose(wV2y, axes=(1,0,2))

    wU2y = preprocess_mat(wU2y)
    wV2y = preprocess_mat(wV2y)

    return wU2y, wV2y

def USCG_drift(Ws_ms, Cs_ms, Dt, Crft):
    ############ Choice of craft ###################

    if Crft == 1:
        # sampan
        Sl = 0.04
        Yt = 0.00
        Da = 48
    elif Crft == 2:
        # skiff
        Sl = 0.03
        Yt = 0.08
        Da = 15
    elif Crft == 3:
        # sailboat
        Sl = 0.03
        Yt = 0.00
        Da = 48
    elif Crft == 4:
        # sail raft
        Sl = 0.08
        Yt = -0.17
        Da = 33
    elif Crft == 5:
        # no sail raft
        Sl = 0.015
        Yt = 0.17
        Da = 17
    elif Crft == 6:
        # sea kayak
        Sl = 0.011
        Yt = 0.24
        Da = 15
    else:
        raise RuntimeError('Unknown craft type')

    ##### Convertions 1 ####################
    ####  knots=m/s*1.94

    Ws_k = Ws_ms * 1.94  # Ws_ms to knots

    ############# The current drift

    Dx_Uc = Cs_ms[0] * Dt  # current zonal drift
    Dy_Vc = Cs_ms[1] * Dt  # current merid. drift

    Ls_k = np.zeros((2,))
    Ld = np.zeros((2,))
    T_drft = np.zeros((2,))
    if Crft != 7:

        Da_rad = (2 * np.pi * Da) / 360  # Da to radians

        ################# total leeway speed (Ls_k) depending on Ws_k

        if abs(Ws_k[0]) > 6:
            Ls_k[0] = (Sl * Ws_k[0]) + Yt
        else:
            Ls_k[1] = (Sl + (Yt / 6)) * Ws_k[0]

        if abs(Ws_k[1]) > 6:
            Ls_k[1] = (Sl * Ws_k[1]) + Yt
        else:
            Ls_k[1] = (Sl + (Yt / 6)) * Ws_k[1]

        ##### Convertions 2 ###################
        ####  m/s=knots*0.51

        Ls_ms = Ls_k * 0.51

        #### use speed to calculate linear displacement Ld
        Ld[0] = Ls_ms[0] * Dt  # disp.due to U wind drift
        Ld[1] = Ls_ms[1] * Dt  # disp.due to V wind drift

        ### the deflections due to Da half right
        ### and  half left of the wind
        coin = np.random.rand()
        if coin > .5:
            flp = 1
        else:
            flp = -1

        Dx_Uw = Ld[0] * np.cos(Da_rad)  # zonal wind zonal drift
        Dy_Uw = Ld[0] * np.sin(Da_rad * flp)  # zonal wind merid. drift

        Dx_Vw = Ld[1] * np.sin(Da_rad * -flp)  # merid. wind zonal drift
        Dy_Vw = Ld[1] * np.cos(Da_rad)  # merid. wind merid. drift

        #########################################################
        ######### The total drift (wind +current) in km ##########

        T_drft[0] = (Dx_Uw + Dx_Vw + Dx_Uc) / 1e+3  # zonal
        T_drft[1] = (Dy_Uw + Dy_Vw + Dy_Vc) / 1e+3  # merid.

    ########### total leeway for the Levison method.
    if Crft == 7:

        aWs_k = abs(Ws_k)
        sz = np.sign(Ws_k[0])
        sm = np.sign(Ws_k[1])
        # zonal component
        if aWs_k[0] < 1:
            Ls_k[0] = 0
        elif 1 <= aWs_k[0] <= 3:
            Ls_k[0] = 0.5 * sz
        elif 3 < aWs_k[0] <= 6:
            Ls_k[0] = 1 * sz
        elif 6 < aWs_k[0] <= 10:
            Ls_k[0] = 2 * sz
        elif 10 < aWs_k[0] <= 16:
            Ls_k[0] = 3 * sz
        elif 16 < aWs_k[0] <= 21:
            Ls_k[0] = 4.5 * sz
        elif 21 < aWs_k[0] <= 27:
            Ls_k[0] = 6 * sz
        elif 27 < aWs_k[0] <= 33:
            Ls_k[0] = 7 * sz
        elif 33 < aWs_k[0] <= 40:
            Ls_k[0] = 6 * sz
        elif aWs_k[0] > 40:
            Ls_k[0] = 4.5 * sz

        # meridional component
        if aWs_k[1] < 1:
            Ls_k[1] = 0
        elif 1 <= aWs_k[1] <= 3:
            Ls_k[1] = 0.5 * sm
        elif 3 < aWs_k[1] <= 6:
            Ls_k[1] = 1 * sm
        elif 6 < aWs_k[1] <= 10:
            Ls_k[1] = 2 * sm
        elif 10 < aWs_k[1] <= 16:
            Ls_k[1] = 3 * sm
        elif 16 < aWs_k[1] <= 21:
            Ls_k[1] = 4.5 * sm
        elif 21 < aWs_k[1] <= 27:
            Ls_k[1] = 6 * sm
        elif 27 < aWs_k[1] <= 33:
            Ls_k[1] = 7 * sm
        elif 33 < aWs_k[1] <= 40:
            Ls_k[1] = 6 * sm
        elif aWs_k[1] > 40:
            Ls_k[1] = 4.5 * sm

        # converting from knots to m/s
        Ls_ms = Ls_k * 0.51

        #### use speed to calculate linear displacement Ld
        Ld[0] = Ls_ms[0] * Dt  # disp.due to U wind drift
        Ld[1] = Ls_ms[1] * Dt  # disp.due to V wind drift

        T_drft[0] = (Ld[0] + Dx_Uc) / 1e+3  # zonal
        T_drft[1] = (Ld[1] + Dy_Vc) / 1e+3  # merid.

    return T_drft