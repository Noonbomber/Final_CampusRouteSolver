Campus Route Solver
By: Landon Schultz
Numerical Methods of Python Final Project

----- Project Description -----
This project is a campus route optimizer for the Southeastern section of OSU campus. 
The program models part of campous as a weighted network of roads, sidewalks, buildings
or points of interest, and parking lot acess points.  The user can select a start and 
end location, as well as a method of travel.  The program uses dijkstra's algorithm to 
find the best route and displays it on a static GPS layout of the campus. You can 
choose between one of 4 methods of travel, walking, biking, scooter, or driving, with 
each different method having different rules it must follow.

----- How To Run The Main Program -----
to run program, put the following in your terminal at the location of the project folder:

python route_app.py

This pulls up the ui and allows you to set two different routes up for the different
methods of travel, time or distance optimization, start and end location, and where
you parked your car if you drove on campus

----- Other Useful Files -----
route_app.py:
The meat and taters of the project, opens the UI, lets the user select the routes,
plots the results of the route, and compares different routes.

route_solver.py:
This file builds the graph from the master map data and solves the route using 
dijkstra's algorithm

numerical_methods.py:
Contains the numerical testing methods for the project, including interpolation 
error analyusis, bisection method calculation for when a scooter becomes faster 
than walking.

map_viewer.py:
Allows you to view all the paths and nodes on the map without any other calculations
running in the background, mainly used for testing

master_mapping_tool.py:
This is the tool I made to layout all of the roads, intersections, sidewalks, parking 
lot entrances, and places of interest and output it to a data file.  This allowed me to
get the nice finalized web of interconnected nodes and paths for the project

settings.py:
This just stores the map bounds, level of zoom or detail on the map, travel speeds of 
modes of travel, and other common constants used for the project

data/master_map_data.csv:
The main data file for the project, housing all the nodes and paths with different ID's 
for dijkstra's algorithm to mull through and find the best solution to the problem.

----- Required Python Libraries -----
matplotlib:
you know this one, I know this one, who doesn't know this one at this point of
the class

contextily:
this library loads the map tiles, instead of using a giant image of the map, it 
allows me to download map tiles from the coordinates of the northeast and southwest
corners of where I wanted to be represented of campus.  This basically just gives a 
small map that can be zoomed into and panned around with.

pyproj:
This library is used to convert longitude and latitude coordinates into map
coordinates that are easier to plot and measure with.  The points in the data
file are saved as longitude and latitude, but for distance calculations the
program needs the points in a projected coordinate system.  pyproj handles that
conversion.

If needed, install them with:

python -m pip install matplotlib contextily pyproj

----- Travel Mode Rules -----
Walking:
Walking is the simplest method of travel in the project.  Walking only uses the 
sidewalk paths and the little access paths that connect buildings and POI's to 
the sidewalk network.  Walking is also allowed to cross roads where the sidewalks 
connect to a road or road intersection, since this is basically acting like a 
crosswalk, and remember, no walking on the grass.

Biking:
Bikes are allowed to use both roads and sidewalks.  This makes biking more 
flexible than walking or driving, because it can use basically the whole route 
network.  For simplicity, I assumed that bikes can be locked up around any 
building or point of interest, so there is no parking lot step for biking.

Scooter:
Scooters work mostly the same as bikes in the route rules, meaning they can use 
both sidewalks and roads.  The main difference is speed.  The scooter speed is 
estimated with interpolation depending on the length of the segment, since a 
scooter probably will not be going full speed on every tiny little sidewalk 
segment.

Car:
Cars can only drive on roads.  Since you can not just drive straight into most 
buildings on campus, the driving route is split up into a few parts.  The user 
selects where their car was parked first, then the program does the following:
-->walk from the start location to the parked car
-->drive from that parking lot to the best destination parking lot
-->walk from the destination parking lot to the final location
Cars also have a small time penalty added at road intersections.  This is meant 
to account for slowing down, stopping, turning, and just generally not being able 
to go full speed through every intersection, basically no running red lights or 
stop signs.


----- Numerical Methods Used -----
Dijkstra's Algorithm:
The main algorithm for the project is dijkstra's algorithm.  The campus is 
treated as a big graph, where each node is a point on campus and each edge is a 
road, sidewalk, parking access, or building access path.  Dijkstra's algorithm 
then goes through the graph and finds the lowest cost way to get from the start 
point to the end point.

Weighted Graphs:
All of the paths are weighted connections.  The weight can either be the distance 
of the path or the estimated travel time depending on what the user selects.  
This is what allows the same map to give different routes depending on the mode 
of travel.

Interpolation:
The interpolation part is used for the scooter speed.  Instead of just assuming 
the scooter is always going the exact same speed, I used linear interpolation to 
estimate the scooter speed based on the segment length.  This gives slower speeds 
on short segments and faster speeds on longer segments.

Bisection Method:
The bisection method is used to find the distance where using a scooter becomes 
faster than walking.  This is basically solving for when the walking time and 
scooter time are equal.

Comparison:
The UI allows two completely different routes to be compared.  This means you 
can compare walking vs driving, biking vs scooter, or even routes with different 
start and end points.  This is also useful for seeing how optimizing by time 
changes things compared to optimizing by distance.