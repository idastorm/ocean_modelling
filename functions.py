#import functions and modules:
from ipywidgets import Dropdown, ColorPicker, VBox, HBox, Output, Button, Checkbox, Tab, Label
from ipywidgets import interact, interact_manual, Dropdown, SelectMultiple, HBox, VBox, Button, Output, FloatText, IntText, IntRangeSlider, RadioButtons,IntProgress, Checkbox, GridspecLayout, Text
from IPython.display import clear_output
from IPython.core.display import display, HTML
import matplotlib.pyplot as plt
from matplotlib.colors import rgb2hex

import pandas as pd
import numpy as np
import traceback
import warnings
warnings.filterwarnings("ignore")

#for drawing the study area:
import json
from ipyleaflet import Map, basemaps, basemap_to_tiles, DrawControl, GeoJSON, LayersControl,SplitMapControl, FullScreenControl
#draw study area - search
from ipyleaflet import Map, SearchControl, Marker, AwesomeIcon
# import ipywidgets

import sys
sys.path.append('../voyager')

from voyager.core import Simulation

#map with gojson files:
  
# import os
# import json
# import random
# import requests

from ipyleaflet import Map, GeoJSON
    
def create_map(map_type='Street map'):
    
    street_map  = basemap_to_tiles(basemaps.Esri.WorldStreetMap)
    imagery_map = basemap_to_tiles(basemaps.Esri.WorldImagery)

    # Create a Map object m
    if map_type=='Street map':
        m = Map(layers=(street_map, ), zoom=2)
    else:
        m = Map(layers=(imagery_map, ), zoom=2)
    
    # List of controls
    # Add more as needed
    search_control = SearchControl(position="topright",
                                url='https://nominatim.openstreetmap.org/search?format=json&q={s}',
                                zoom=5,
                                marker=Marker(icon=AwesomeIcon(name="check", 
                                                               marker_color='green', 
                                                               icon_color='darkgreen')))

    # draw_control = DrawControl(rectangle={'shapeOptions': {'color': '#0000FF'}})
    # draw_control.on_draw(widget.draw_callback)

    fullscreen_control = FullScreenControl()
    layers_control = LayersControl(position='topright')

    controls = [search_control, fullscreen_control, layers_control]

    # Add all control listeners to map model
    for control in controls:
        m.add_control(control)


    # m.on_interaction(widget.handle_click)

    return m
    

class MapWidget:

    def __init__(self) -> None:
        
        # map_for_selection = draw_studyarea(map_type='Street map')
        start_date = pd.Timestamp('1993-01-01')
        end_date   = pd.Timestamp('2018-12-31')

        dates   = pd.date_range(start_date, end_date)
        self.years   = dates.year.unique()
        self.months  = dates.month.unique()
        days    = list(range(1, 31))

        # Vessels names
        vessels_tuple = [('Commercial Fishing Vessels',1),
                         ('Skiffs',2),
                         ('Mono-hull Sailing Vessel',3),
                         ('Rustic raft with sail',4),
                         ('Rustic raft without sail',5),
                         ('Sea kayak', 6)]

        self.bbox = None
        self.target = None
        self.markers = []
        self.targets = []

        # Styles
        style_bin = {'description_width': 'initial'}

        self.fields = {"start year": Dropdown(options = self.years,
                                           description = 'Start year',
                                           disabled= False),
                                           
                    "start month": Dropdown(options = self.months,
                                           description = 'Start month',
                                           disabled= False),

                    "start day": Dropdown(options=days,
                                          description = 'Start day',
                                          disabled= False),

                    "end year": Dropdown(options = self.years,
                                           description = 'End year',
                                           disabled= False),
                                           
                    "end month": Dropdown(options = self.months,
                                           description = 'End month',
                                           disabled= False),

                    "end day": Dropdown(options = days,
                                           description = 'End day',
                                           disabled= False),

                    "launch interval": IntText(value=5, 
                                               style=style_bin, 
                                               description='Launch interval (days):', 
                                               disabled=False),

                    "journey length": IntText(value=60,
                                              style=style_bin,
                                              description='Max journey length (days):',
                                              disabled=False),

                    "timestep": IntText(value=24,
                                              style=style_bin,
                                              description='Timestep (hours):',
                                              disabled=False),
                                           
                    "displacement": RadioButtons(options=['Drift','Paddling', 'Sailing'],
                                                 value='Drift',
                                                 description=' ',
                                                 disabled=False),

                    "vessel type": Dropdown(options = vessels_tuple,
                                            style=style_bin,
                                            value = 1,
                                            rows = 4,
                                            description = 'Vessel type:',
                                            disabled = False),
                    
                    "data": Text(value='/data/cdhdata/voyager/',
                                style= style_bin,
                                description='Data directory:',
                                disabled=False),

                    "update": Button(description='Run simulation',
                                     disabled=False,
                                     button_style='danger', # 'success', 'info', 'warning', 'danger' or ''
                                     tooltip='Simulates trajectories in map selection',),
        }


        pass

    def start_year_change(self, action):

        end_years = np.array(self.fields["end year"].options)
        selected_year = self.fields["start year"].value

        # Update end years to only allow years above 
        # current start year value
        self.fields["end year"].options = end_years[end_years >= selected_year].tolist()
        
    def end_year_change(self, action):

        if self.fields["end year"].value == self.fields["start year"].value:

            end_months = np.array(self.months)
            selected_month = self.fields["start month"].value

            self.fields["end month"].options = end_months[end_months >= selected_month].tolist()

        else:

            self.fields["end month"].options = self.months

    def start_month_change(self, action):

        same_year = self.fields["start year"].value == self.fields["end year"].value
        same_month = self.fields["start month"].value == self.fields["end month"].value
        
        start_year = self.fields["start year"].value
        end_year   = self.fields["end year"].value
        month      = self.fields["start month"].value

        # Calculate the number of days in the month of that year
        # This is important, since the data is leap year sensitive
        self.fields["start day"].options = list(range(1, pd.Timestamp(f"{start_year}-{month}").days_in_month + 1))

        end_months = np.array(self.months)
        selected_month = self.fields["start month"].value

        self.fields["end month"].options = end_months[end_months >= selected_month].tolist()

        # if start_year == end_year or len(self.fields["end month"].options)==0:

        #     updated_list=[]
        #     for item in s_month.options:
        #         if item>=int(c['new']):

        #             updated_list.append(item)

    def end_month_change(self, action):

        same_year = self.fields["start year"].value == self.fields["end year"].value
        same_month = self.fields["start month"].value == self.fields["end month"].value

        if same_year and same_month:

            end_days = np.array(self.fields["end day"].options)
            selected_day = self.fields["start day"].value

            self.fields["end day"].options = end_days[end_days > selected_day].tolist()

        else:

            start_year = self.fields["start year"].value
            end_year   = self.fields["end year"].value
            month      = self.fields["end month"].value

            # Calculate the number of days in the month of that year
            # This is important, since the data is leap year sensitive
            self.fields["end day"].options = list(range(1, pd.Timestamp(f"{end_year}-{month}").days_in_month + 1))
            
    def day_change(self, action):

        same_year = self.fields["start year"].value == self.fields["end year"].value
        same_month = self.fields["start month"].value == self.fields["end month"].value

        if same_year and same_month:
            
            end_days = np.array(self.fields["end day"].options)
            selected_day = self.fields["start day"].value

            self.fields["end day"].options = end_days[end_days > selected_day].tolist()

    def displacement_change(self, action):

        if self.fields["displacement"].value == 'Paddling' or self.fields["displacement"].value == 'Sailing':

            vessels_tuple = [('Log boat',1),
                            ('Plank built boat',2),
                            ('Skin boat',3),
                            ('Bark boat',4)]

        else:

            vessels_tuple = [('Commercial Fishing Vessels',1),
                            ('Skiffs',2),
                            ('Mono-hull Sailing Vessel',3),
                            ('Rustic raft with sail',4),
                            ('Rustic raft without sail',5),
                            ('Sea kayak', 6)]

        self.fields["vessel type"].options = vessels_tuple

    def draw_callback(self, this, action, geo_json):

        # print(geo_json)
        # print(self.markers)
        # print(geo_json["properties"]["style"].keys())

        if geo_json["geometry"]["type"] == "Polygon":

            if action == "created":

                x0, y0  = geo_json["geometry"]["coordinates"][0][0]
                x1, y1  = geo_json["geometry"]["coordinates"][0][2]

                self.bbox = [x0, y0, x1, y1]

            elif action == "deleted":

                self.bbox = None
        
        elif (geo_json["geometry"]["type"] == "Point") and ("shapeOptions" in geo_json["properties"]["style"].keys()):

            coords = geo_json["geometry"]["coordinates"]

            if action == "created":
                
                self.markers.append(coords)

            elif action == "deleted":

                self.markers.remove(coords)

            else:
                pass

        elif (geo_json["geometry"]["type"] == "Point") and not ("shapeOptions" in geo_json["properties"]["style"].keys()):

            coords = geo_json["geometry"]["coordinates"]

            if action == "created":

                self.target = coords

            elif action == "deleted":

                self.target = None

            else:
                pass

        else:
            pass


    def marker_draw_callback(self, this, action, geo_json):

        
        if geo_json["geometry"]["type"] == "Point":

            coords = geo_json["geometry"]["coordinates"]

            if action == "created":
                
                self.targets.append(coords)

            elif action == "deleted":

                self.targets.remove(coords)

            else:
                pass
            

    def draw(self):

        # Create a map
        self.m = create_map()

        # Add some draw controls and get the values
        draw_control = DrawControl( polyline={}, polygon={})

        draw_control.circlemarker = {
            "shapeOptions": {
                "fillColor": "#efed69",
                "color": "#efed69",
                "fillOpacity": 0.5,
                "radius": 1
            }
        }

        draw_control.marker = {'draggable': True}

        draw_control.rectangle = {
            "shapeOptions": {
                "color": "#fca45d",
                "fillOpacity": 0
            }
        }

        # The draw callback sets
        # the bbox and markers properties
        draw_control.on_draw(self.draw_callback)
        self.m.add_control(draw_control)

        header_map = Output()
        header_date = Output()
        header_simulation_settings = Output()
        space_vessel_settings = Output()

        with header_map:
            display(HTML('<p style="font-size:15px;font-weight:bold;"><br>Draw a rectangle of the area where the simulation should run: </p>'))

        with header_date:
            display(HTML('<p style="font-size:15px;font-weight:bold;"><br>Select date range for simulations: </p>'))
        
        with header_simulation_settings:
            display(HTML('<p style="font-size:15px;font-weight:bold;"><br>Simulation specifications: </p>'))
            
        with space_vessel_settings:
            display(HTML('<p style="font-size:5px;font-weight:bold;"><br> </p>'))

        ############ DATES ##############
        # Draw date boxes vertically stacking the 
        # years, months and days
        year_box    = VBox([self.fields["start year"], self.fields["end year"]])
        month_box   = VBox([self.fields["start month"], self.fields["end month"]])
        day_box     = VBox([self.fields["start day"], self.fields["end day"]])

        year_box.layout.margin = '0px 0px 0px 0px'
        # Horizontal stacking of the dates
        date_box = HBox([year_box, month_box, day_box])
        date_box.layout.margin = '25px 0px 10px 0px'

        ########## JOURNEY #############
        # Horizontal alignment of launch intervals and journey length
        journey_box = HBox([self.fields["launch interval"], self.fields["journey length"], self.fields["timestep"]])
        
        ########## VESSELS ############
        vessel_box = VBox([space_vessel_settings, self.fields["vessel type"]])
        data_box = VBox([space_vessel_settings, self.fields["data"]])
        vessel_settings_box = VBox([self.fields["displacement"], self.fields["vessel type"], self.fields["data"]])

        self.fields["vessel type"].layout.margin = '36px 0px 0px 0px'
        self.fields["displacement"].layout.margin = '15px 0px 0px 0px' #top, right, bottom, left

        ######### UPDATE ##############
        update_button = self.fields["update"]
        update_button.layout.margin = '80px 0px 0px 50px' #top, right, bottom, left
        update_button.style.button_color= '#4169E1'

        def on_button_click(button):

            try:
                print("Loading data for region...")
                sim = Simulation(model=self.fields["displacement"].value.lower(),
                                                craft=self.fields["vessel type"].value,
                                                duration=self.fields["journey length"].value,
                                                timestep=self.fields["timestep"].value * 60 * 60,
                                                target_point=self.target,
                                                start_date=f'{self.fields["start year"].value}-{self.fields["start month"].value}-{self.fields["start day"].value}',
                                                end_date=f'{self.fields["end year"].value}-{self.fields["end month"].value}-{self.fields["end day"].value}',
                                                launch_freq=self.fields["launch interval"].value,
                                                bbox=self.bbox,
                                                departure_points=self.markers,
                                                data_directory=self.fields["data"].value,
                                                )
                print("- Data loaded!")
                print("Starting simulation...")
                sim.run('results.geojson')
                print("- Simulation finished!")

                with open('results.geojson', 'r') as f:
                    data = json.load(f)

                if len(self.m.layers) > 1:
                    self.m.remove_layer(self.m.layers[1])
                    
                def style_callback(feature):

                    cmap = plt.get_cmap('hot')
                    launch_date = pd.Timestamp(feature["properties"]['date']).month/12
                    color = cmap(launch_date)

                    

                    return {'color': rgb2hex(color), 'opacity': 0.5, 'weight': 2}

                trajectory_dict = {k: {"type": "FeatureCollection",
                                       "features": []} for k in range(1, 13)}

                for trajectory in data["features"]:

                    trajectory_month = pd.Timestamp(trajectory['properties']['data']).month
                    trajectory_dict[trajectory_month]["features"].append(trajectory)

                # for trajectory in data["features"]:
                    

                for month_id in range(1, 13):

                    data_layer = GeoJSON(data=trajectory_dict[month_id], 
                                        # name=pd.Timestamp(trajectory["properties"]["date"],
                                    name = month_id,
                                            #  style={'Line': '9'},s
                                    hover_style={'color': 'yellow', 'opacity': 1}, 
                                    style_callback=style_callback
                                    )
                     self.m.add_layer(data_layer)
                    
                # data_layer = GeoJSON(data=data, 
                #                         # name=pd.Timestamp(trajectory["properties"]["date"],
                #                     name = "trajectories",
                #                             #  style={'Line': '9'},s
                #                     hover_style={'color': 'yellow', 'opacity': 1}, 
                #                     style_callback=style_callback
                #                     )



                # self.m.add_layer(data_layer)

            except Exception as exc:

                print(exc)

                print(traceback.format_exc())

        # This callback runs the simulation
        update_button.on_click(on_button_click)

        # update_button.on_click(print)

        ######### Assemble ############
        form = VBox([header_map, 
                    self.m, 
                    header_date,
                    date_box,
                    header_simulation_settings,
                    journey_box,
                    vessel_settings_box, 
                    self.fields["update"]])

        #Initialize form output:
        form_out = Output()

        #Initialize results output widgets:
        #only use for progress bar currently
        header_output = Output()
        
        #example map output with example geojson (old trajectories):
        output_example_map = Output()

        # Observe changes and update values in these fields
        changeables = ["start year", "start month", "end year", "start day", "end month", "displacement"]
        observers   = {"start year": self.start_year_change, 
                       "start month": self.start_month_change, 
                       "end year": self.end_year_change, 
                       "start day": self.day_change,
                       "end month": self.end_month_change, 
                       "displacement": self.displacement_change
        }

        for changeable in changeables:

            self.fields[changeable].observe(observers[changeable], 'value')


        with form_out:
        
            display(form,header_output,output_example_map)

        #Display form:
        display(form_out)
