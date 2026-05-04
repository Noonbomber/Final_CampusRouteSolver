# Author: Landon Schultz
# Date: 5-3-26

### Settings for the campus route solver project

#Campus map area in longitude and latitude
#Format is west, south, east, north
#This is the smaller campus chunk from Cleveland/Hall of Fame to Duck/University
#These bounds were picked manually with bounds_picker.py
CAMPUS_BOUNDS_LONLAT = (-97.07610187040834, 36.119189273754095, -97.06188887599457, 36.127479902794136)

#Map tile zoom level
#17 seems like the best mix between detail and not downloading a ton of tiles
MAP_ZOOM = 17

#Different colors for the path types
PATH_COLORS = {
    "sidewalk": "tab:green",
    "road": "tab:gray",
    "crosswalk": "tab:orange",
}

#Different transportation types for later in the project
TRANSPORT_TYPES = ["walk", "bike", "scooter", "car"]

#Path types allowed for each transportation type
ALLOWED_PATHS = {
    "walk": ["sidewalk", "crosswalk", "road"],
    "bike": ["sidewalk", "crosswalk", "road"],
    "scooter": ["sidewalk", "crosswalk", "road"],
    "car": ["road"],
}

#Rough average speeds for later time calculations
#These are in miles per hour
SPEEDS_MPH = {
    "walk": 3.0,
    "bike": 10.0,
    "scooter": 12.0,
    "car": 18.0,
}
