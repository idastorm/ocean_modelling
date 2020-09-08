from utils import *
import numpy as np
from tqdm import tqdm
from scipy.interpolate import RegularGridInterpolator
from netCDF4 import Dataset
import datetime
import multiprocessing as mp
import os
import argparse

# parser = argparse.ArgumentParser()
# parser.add_argument('--config', default='test.json', help="Name of .json file")



if __name__ == '__main__':

     # Parse arguments to program
    # args = parser.parse_args()

    # Get configuration JSON file
    # config_name = args.config
    # config_path = os.path.join("config/", config_name)

    # Read the configuration file
    # with open(config_path) as json_file:
        # config = json.load(json_file)

    # wind_path    = config["path to wind data"]
    # current_path = config["path to current data"]
    # mask_path    = config["path to mask data"]

    # lat_min = config["min latitude"]
    # lat_max = config["max latitude"]
    # lon_min = config["min longitude"]
    # lon_max = config["max longitude"]

    # day_frequency = config["launch frequency in days"]
    # craft_type    = config["USCG craft type"]

    # dt = config["timestep in days"]
    # max_days_to_run = config["max days to simulate trajectory"]
    # start_date = datetime.date.fromisoformat(config["start date"])
    
    lat_min = 20
    lat_max = 45
    lon_min = -30+360
    lon_max = -5+360

    day_frequency    = 5
    craft_type       = 5
    dt               = 1
    max_days_to_run  = 60
    factor           = 12
    n_days           = factor*30-max_days_to_run

    days = np.arange(0, n_days, day_frequency)
    start_date = datetime.date.fromisoformat('1979-01-01')
    time_delta = datetime.timedelta(days=day_frequency)


    # lon, lat, area   = get_local_coordinates(bbox, mask)
    # departure_points = get_departure_points(bbox, mask)

    # Read data and transform to 
    data = Dataset("data/wind.nc", "r", format="NETCDF4")
    mask_data = Dataset("data/lsm.nc", "r", format="NETCDF4")
    mask = np.array(mask_data.variables["lsm"]).squeeze() > 0.5

    longitude = np.array(data.variables["longitude"])
    latitude  = np.array(data.variables["latitude"])

    
    # Extract bounding box and transform to longitude, latitude masks
    bbox             = (lon_min, lat_min, lon_max, lat_max)
    lon_mask, lat_mask = get_bbox_mask(longitude, latitude, bbox)

    lon = longitude[lon_mask]
    lat = latitude[lat_mask]

    departure_points = get_departure_points(mask[lat_mask][:, lon_mask], lon, lat)

    random_launch_sites = np.random.choice(np.arange(departure_points.shape[0]), 236)

    departure_points = departure_points[random_launch_sites, :]

    # Mask the data
    u = np.array(data.variables["u10"])#[days, :, :]
    v = np.array(data.variables["u10"])#[days, :, :]
    u[:, mask] = np.nan
    v[:, mask] = np.nan

    # Extract relevant area of wind and currents
    all_dates_wind_x = np.repeat(np.flip(u[:, lat_mask][:, :, lon_mask], axis=2), factor, axis=0)
    all_dates_wind_y = np.repeat(np.flip(v[:, lat_mask][:, :, lon_mask], axis=2), factor, axis=0)

    all_dates_current_x = 0.1*all_dates_wind_x  # Should obviously be changed
    all_dates_current_y = 0.1*all_dates_wind_y

    # Extract relevant area of the longitude and latitudes
    lon = longitude[lon_mask]
    lat = latitude[lat_mask]

    # Fetch a year of data
    time = np.arange(all_dates_current_x.shape[0])

    # current_in_x = RegularGridInterpolator((time, lat[::-1], lon), all_dates_current_x, bounds_error=False, fill_value=np.nan)
    # current_in_y = RegularGridInterpolator((time, lat[::-1], lon), all_dates_current_y, bounds_error=False, fill_value=np.nan)
        
    # wind_in_x = RegularGridInterpolator((time, lat[::-1], lon), all_dates_wind_x, bounds_error=False, fill_value=np.nan)
    # wind_in_y = RegularGridInterpolator((time, lat[::-1], lon), all_dates_wind_y, bounds_error=False, fill_value=np.nan)

    all_results = {}
    date = start_date
    for launch_day in tqdm(days):

        
        current_in_x = RegularGridInterpolator((lat[::-1], lon), all_dates_current_x[launch_day, :, :], bounds_error=False, fill_value=np.nan)
        current_in_y = RegularGridInterpolator((lat[::-1], lon), all_dates_current_y[launch_day, :, :], bounds_error=False, fill_value=np.nan)
            
        wind_in_x = RegularGridInterpolator((lat[::-1], lon), all_dates_wind_x[launch_day, :, :], bounds_error=False, fill_value=np.nan)
        wind_in_y = RegularGridInterpolator((lat[::-1], lon), all_dates_wind_y[launch_day, :, :], bounds_error=False, fill_value=np.nan)

        # Send out a number of vessels every day (sigh)
        vessels  = [Vessel(np.array([x]), np.array([y]), craft=craft_type) for x, y in departure_points]
        options =  [(vessel, launch_day, max_days_to_run, dt, lon, lat, (current_in_x, current_in_y), (wind_in_x, wind_in_y)) for vessel in vessels]

        with mp.Pool(mp.cpu_count()) as p:
            # results = [p.apply_async(simulate_vessel_trajectory, args=(vessel, launch_day, max_days_to_run, dt, lon, lat, (current_in_x, current_in_y), (wind_in_x, wind_in_y)))for vessel in vessels]
            # result = [process.get() for process in results]

            results = p.starmap(simulate_vessel_trajectory, options)
            all_results[date.strftime("%Y-%m-%d")] = results

        # for vessel in vessels:
            # simulate_vessel_trajectory(vessel, launch_day, max_days_to_run, dt, lon, lat, (current_in_x, current_in_y), (wind_in_x, wind_in_y))

        date += time_delta
    
    save_to_GeoJSON(all_results, "GeoJSON/results.json")
