# Author: Landon Schultz
# Date: 5-3-26

#The main testing file for the map and transport settings

#Campus corners to be loaded in order of w, s, e, and n, I had to really zone in the area manually after looking up the general coordinates
CAMPUS_BOUNDS_LONLAT = (-97.07610187040834, 36.119189273754095, -97.06188887599457, 36.127479902794136)

#This says how defined the map tiles that get downloaded are, 
MAP_ZOOM = 17

#This just allows you to see the paths a bit better on the map
PATH_COLORS = {
    "sidewalk": "tab:green",
    "road": "tab:gray",
    "crosswalk": "tab:orange",
}

#Different transportation types for later in the project
TRANSPORT_TYPES = ["walk", "bike", "scooter", "car"]

#The different paths each transport can go on
ALLOWED_PATHS = {
    "walk": ["sidewalk", "crosswalk", "road"],
    "bike": ["sidewalk", "crosswalk", "road"],
    "scooter": ["sidewalk", "crosswalk", "road"],
    "car": ["road"],
}

#average speeds of the modes of transportation, just kinda guesstimates
SPEEDS_MPH = {
    "walk": 3.0,
    "bike": 10.0,
    "scooter": 12.0,
    "car": 18.0,
}