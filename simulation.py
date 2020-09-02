from utils import *
import numpy as np
from tqdm import tqdm
from scipy.interpolate import RegularGridInterpolator
from skimage import measure

import multiprocessing as mp

if __name__ == '__main__':


    class Vessel:

        def __init__(self, x, y, craft: int):

            self.craft = craft
            self.x = x
            self.y = y
            self.trajectory = [[self.x, self.y]]

        def update_position(self, x, y):
            
            self.x = x
            self.y = y

            self.trajectory.append([x, y])

    # departure_points = loadmat('Dep_dist')['Dep_dist']

    #ex 139.05910815 1477.48753329
    #access via ex departure_points[0][0] -- in distance coordinates (X and Y) from lower left corner (?)
    #print(departure_points[0][0])


    #lon and lat depend on previously defined area (pro-processing to drift)
    #len=1 (list of lists), len[lon[0]]=106
    #-32 to -5.75 degrees
    #see area in map - "Map: show study area"
    # lon = loadmat('Atl_lon.mat')['Atl_lon'].squeeze()

    #len[lat[0]]=95
    #20-43.5 degrees
    # lat = loadmat('Atl_lat.mat')['Atl_lat'].squeeze()

    #len(X)= 95 len X[0]= 106
    # X = loadmat('X_dist')['X_dist']

    #len 106
    # Y = loadmat('Y_dist')['Y_dist']

    # vector with distance between x (e-w) grid points
    #len 95
    # Dx = loadmat('Dx.mat')['Dx']
    # All rows in column 1
    # Dx=Dx[:,0]

    # vector with distance between y (n-s) grid points
    #also len 95
    # Dy = loadmat('Dy.mat')['Dy']
    # All rows in column 1
    # Dy=Dy[:,0]

    # MDx = max(Dx); # maximum distance between x grid points
    # max_distance = max(Dy); # maximum distance between y grid points

    #land ocean
    # mask = loadmat('Mask')['Mask'][:,:,0]


    overlap = 3/4 # Bin overlap to search adjacent indices for wind and current data: 3/4

    # year to start simulation. original value: 1979. min. val: 1979, max val: 2012.
    start_year = 1979
    # year to end simulation. original value: 1979. min. val: 1979, max val: 2012.
    end_year = start_year +1


    max_days_to_simulate = 60   # Length of simulation in days: 60
    time_resolution_in_days = 1 # Time step in days

    n_days = int(np.ceil(max_days_to_simulate / time_resolution_in_days))   # number of days to save data

    dt = time_resolution_in_days * (24 * 60 * 60) # Time step in seconds


    craft_type  = 5 # Type of vessel in USCG categories: 5 (only drift)

    departure_day_frequency = 5 # Frequency in days between departing vessels: 5


    timesteps       = range(0, n_days)
    years           = range(start_year, end_year)
    departure_days  = range(0, 364, departure_day_frequency)



    
    for year in years:

        # Loads two years of current and wind data
        # yearly_current_x, yearly_current_y = load_current_data(year)
        # yearly_wind_x, yearly_wind_y       = load_wind_data(year)
        
        time = np.arange(yearly_current_x.shape[-1])

        # t_axis = TemporalAxis(np.arange(str(start_year), str(end_year)+'-12-31', dtype='datetime64[D]'))
        current_in_x = RegularGridInterpolator((lon, lat, time), yearly_current_x, bounds_error=False, fill_value=np.nan)
        current_in_y = RegularGridInterpolator((lon, lat, time), yearly_current_y, bounds_error=False, fill_value=np.nan)
        
        wind_in_x = RegularGridInterpolator((lon, lat, time), yearly_wind_x, bounds_error=False, fill_value=np.nan)
        wind_in_y = RegularGridInterpolator((lon, lat, time), yearly_wind_y, bounds_error=False, fill_value=np.nan)
        # current_grid_x   = Grid3D(x_axis, y_axis, t_axis, yearly_current_x)
        # current_grid_y   = Grid3D(x_axis, y_axis, t_axis, yearly_current_y)

        # wind_grid_x   = Grid3D(x_axis, y_axis, t_axis, yearly_wind_x)
        # wind_grid_y   = Grid3D(x_axis, y_axis, t_axis, yearly_wind_y)



        data = {}
        
        for day in tqdm(departure_days):
            #print("Day :", idx+1, " out of ", len(departure_days))

            #current_x, current_y = yearly_current_x[:, :, day: day + n_days], yearly_current_y[:, :, day: day + n_days]
            #wind_x, wind_y       = yearly_wind_x[:, :, day: day + n_days], yearly_wind_y[:, :, day: day + n_days]

            # current_x = pad_borders(current_x, np.nan)
            # current_y = pad_borders(current_y, np.nan)

            ############### THIS SHOULD BE ONE FUNCTION ##################
            # Observe the order of coordinates (y, x) in departure_points
            vessels         = [Vessel(np.array([x]), np.array([y]), craft=craft_type) for y, x in departure_points]

            with mp.Pool(mp.cpu_count()) as p:
                results = [p.apply_async(simulate_vessel_trajectory, args=(vessel, day, timesteps, dt, lon, lat, (current_in_x, current_in_y), (wind_in_x, wind_in_y))) for vessel in vessels]

            # Launch new vessels
            # for vessel in vessels:

                ############### THIS SHOULD BE ONE FUNCTION ##################
                # simulate_vessel_trajectory(vessel, day, timesteps, dt, lon, lat, (current_in_x, current_in_y), (wind_in_x, wind_in_y))
                # print("new vessel")
                # print(vessel.trajectory)