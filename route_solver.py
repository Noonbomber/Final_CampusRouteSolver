# Author: Landon Schultz
# Date: 5-4-26

import csv
import heapq
import math
from pathlib import Path

from settings import SPEEDS_MPH

#Main file for building the graph of the campus and solve routes using dikstra's algorithm

#collect data from the master data file on all the types of paths and nodes
MASTER_FILE = Path("data/master_map_data.csv")

#Just some general assumptions for the code solving, these are left here as settings to tune easier
CAR_INTERSECTION_DELAY = 8.0
BUILDING_CONNECT_DISTANCE = 170.0
PARKING_ROAD_CONNECT_DISTANCE = 80.0
PARKING_SIDEWALK_CONNECT_DISTANCE = 95.0
CROSSING_CONNECT_DISTANCE = 35.0
MERGE_DISTANCE = 8.0
SIDEWALK_GAP_CONNECT_DISTANCE = 20.0

#Function to turn longitude and latitude to mercator coords, making the distance math work
def lonlat_to_web(lon, lat):
    radius = 6378137
    lon_rad = math.radians(lon)
    lat_rad = math.radians(lat)
    x_coord = radius * lon_rad
    y_coord = radius * math.log(math.tan(math.pi / 4 + lat_rad / 2))
    return x_coord, y_coord

#mph to meters per second
def mph_to_mps(speed_mph):
    return speed_mph * 1609.344 / 3600

#general distance function
def xy_distance(point_a, point_b):
    dx = point_b[0] - point_a[0]
    dy = point_b[1] - point_a[1]
    return math.sqrt(dx * dx + dy * dy)

#Function for linear interpolation, much like the lagrange or vandermode from HW3
def linear_interp(x_value, x_points, y_points):

    #if below or above the table, use the end values
    if x_value <= x_points[0]:
        return y_points[0]
    if x_value >= x_points[-1]:
        return y_points[-1]

    #loop through the intervals to find the right one, cause we love loops
    for i in range(len(x_points) - 1):
        if x_points[i] <= x_value <= x_points[i + 1]:
            x0 = x_points[i]
            x1 = x_points[i + 1]
            y0 = y_points[i]
            y1 = y_points[i + 1]

            #linear interpolation formula
            return y0 + (y1 - y0) * (x_value - x0) / (x1 - x0)
    return y_points[-1]

#This is the function for the nonconstant scooter speed, using interpolation to have a scooter that gets faster on longer paths
def scooter_speed_from_distance(distance_m):
    #Distance and speed table values,a lso note that the top speed can be changed in settings
    distance_points = [0, 40, 100, 200, 400]
    speed_points = [5.0, 8.0, 10.0, 11.5, SPEEDS_MPH["scooter"]]
    return linear_interp(distance_m, distance_points, speed_points)

#loading the master data info to this file
def load_master_data():

    data = []
    with MASTER_FILE.open("r", newline="") as file:
        reader = csv.DictReader(file)

        #here we loop through all near 1000 rows, cause we love loops
        for row in reader:
            row["longitude"] = float(row["longitude"])
            row["latitude"] = float(row["latitude"])
            row["point_order"] = int(row["point_order"])
            data.append(row)
    return data

#function for grouping sets of roads or sidewalks together based on location from the csv file
def group_line_features(data, feature_type):

    features = {}
    #loop through the data to group matching features, cause we love loops
    for row in data:
        if row["feature_type"] == feature_type:
            feature_id = row["feature_id"]
            if feature_id not in features:
                features[feature_id] = []
            features[feature_id].append(row)
    for feature_id in features:
        features[feature_id].sort(key=lambda point: point["point_order"])
    return features

#Function for adding all the nodes to the graph
def add_graph_node(graph, node_id, lon, lat, x_coord, y_coord, node_type, name="", point_kind="point"):

    #Load node info from csv
    graph["nodes"][node_id] = {
        "lon": lon,
        "lat": lat,
        "x": x_coord,
        "y": y_coord,
        "type": node_type,
        "name": name,
        "point_kind": point_kind,
    }
    if node_id not in graph["adj"]:
        graph["adj"][node_id] = []

#This function adds the edges to the graph between modes
def add_edge(graph, node_a, node_b, path_type, modes, feature_id=""):

    if node_a == node_b:
        return

    point_a = [graph["nodes"][node_a]["x"], graph["nodes"][node_a]["y"]]
    point_b = [graph["nodes"][node_b]["x"], graph["nodes"][node_b]["y"]]
    distance_m = xy_distance(point_a, point_b)

    edge_ab = {
        "to": node_b,
        "distance_m": distance_m,
        "path_type": path_type,
        "modes": modes,
        "feature_id": feature_id,
        "to_intersection": graph["nodes"][node_b].get("point_kind") == "intersection",
    }
    edge_ba = {
        "to": node_a,
        "distance_m": distance_m,
        "path_type": path_type,
        "modes": modes,
        "feature_id": feature_id,
        "to_intersection": graph["nodes"][node_a].get("point_kind") == "intersection",
    }

    graph["adj"][node_a].append(edge_ab)
    graph["adj"][node_b].append(edge_ba)

#This is the function that merges two segments together based off of the small error from when i was mapping everything, as I am not perfect and cannot place to the accuracy of a singular pixel
def get_or_make_network_node(graph, prefix, lon, lat, x_coord, y_coord, node_type, point_kind):

    #loop through old nodes to see if this point is already basically there
    for node_id, node in graph["nodes"].items():
        if not node_id.startswith(prefix):
            continue
        distance_m = xy_distance([x_coord, y_coord], [node["x"], node["y"]])
        if distance_m <= MERGE_DISTANCE:
            if point_kind == "intersection":
                node["point_kind"] = "intersection"
            return node_id
    node_id = prefix + "_" + str(graph["counters"].get(prefix, 0)).zfill(4)
    graph["counters"][prefix] = graph["counters"].get(prefix, 0) + 1
    add_graph_node(graph, node_id, lon, lat, x_coord, y_coord, node_type, point_kind=point_kind)
    return node_id

#This finds the nearest node of a given type
def nearest_node(graph, x_coord, y_coord, allowed_types):

    best_node = None
    best_distance = float("inf")

    #loop through nodes and keep the closest match, cause we love loops
    for node_id, node in graph["nodes"].items():
        if node["type"] not in allowed_types:
            continue

        distance_m = xy_distance([x_coord, y_coord], [node["x"], node["y"]])

        if distance_m < best_distance:
            best_distance = distance_m
            best_node = node_id

    return best_node, best_distance


#Function for finding nearby nodes of a certain type
def nearby_nodes(graph, x_coord, y_coord, allowed_types, max_distance, max_count=None):
    found_nodes = []
    #loop through nodes and save all of the close ones
    for node_id, node in graph["nodes"].items():
        if node["type"] not in allowed_types:
            continue
        distance_m = xy_distance([x_coord, y_coord], [node["x"], node["y"]])
        if distance_m <= max_distance:
            found_nodes.append([node_id, distance_m])
    found_nodes.sort(key=lambda row: row[1])
    if max_count is not None:
        found_nodes = found_nodes[:max_count]
    return found_nodes


#Function for connecting nodes that are basically touching after my hand mapping
def connect_close_nodes(graph, node_type, max_distance, path_type, modes):
    nodes = [node_id for node_id, node in graph["nodes"].items() if node["type"] == node_type]
    #loop through pairs of nodes, cause we love loops
    for i in range(len(nodes)):
        node_a = nodes[i]
        point_a = [graph["nodes"][node_a]["x"], graph["nodes"][node_a]["y"]]
        for j in range(i + 1, len(nodes)):
            node_b = nodes[j]
            point_b = [graph["nodes"][node_b]["x"], graph["nodes"][node_b]["y"]]
            distance_m = xy_distance(point_a, point_b)
            if distance_m <= max_distance:
                add_edge(graph, node_a, node_b, path_type, modes, path_type)


#Function for building the full campus graph from the csv data
def build_campus_graph():
    data = load_master_data()
    graph = {
        "nodes": {},
        "adj": {},
        "counters": {},
        "locations": {},
        "parking_lots": {},
    }

    #build road line nodes and edges
    road_features = group_line_features(data, "road")
    #loop through every road line from the csv
    for feature_id, points in road_features.items():
        last_node = None
        #loop through the points that make up this road
        for point in points:
            x_coord, y_coord = lonlat_to_web(point["longitude"], point["latitude"])
            node_id = get_or_make_network_node(
                graph,
                "road",
                point["longitude"],
                point["latitude"],
                x_coord,
                y_coord,
                "road",
                point["point_kind"],
            )
            if last_node is not None:
                add_edge(graph, last_node, node_id, "road", ["car", "bike", "scooter"], feature_id)
            last_node = node_id

    #build sidewalk line nodes and edges
    sidewalk_features = group_line_features(data, "sidewalk")
    #loop through every sidewalk line from the csv
    for feature_id, points in sidewalk_features.items():
        last_node = None
        #loop through the points that make up this sidewalk
        for point in points:
            x_coord, y_coord = lonlat_to_web(point["longitude"], point["latitude"])
            node_id = get_or_make_network_node(
                graph,
                "sidewalk",
                point["longitude"],
                point["latitude"],
                x_coord,
                y_coord,
                "sidewalk",
                point["point_kind"],
            )
            if last_node is not None:
                add_edge(graph, last_node, node_id, "sidewalk", ["walk", "bike", "scooter"], feature_id)
            last_node = node_id

    #add buildings and POIs and connect them to nearby sidewalks
    for row in data:
        if row["feature_type"] not in ["building", "poi"]:
            continue
        x_coord, y_coord = lonlat_to_web(row["longitude"], row["latitude"])
        node_id = row["feature_id"]
        add_graph_node(
            graph,
            node_id,
            row["longitude"],
            row["latitude"],
            x_coord,
            y_coord,
            row["feature_type"],
            row["feature_name"],
        )
        graph["locations"][node_id] = row["feature_name"]
        near_sidewalks = nearby_nodes(
            graph,
            x_coord,
            y_coord,
            ["sidewalk"],
            BUILDING_CONNECT_DISTANCE,
            max_count=4,
        )
        #loop through nearby sidewalks so the building can connect to the network
        for near_sidewalk, distance_m in near_sidewalks:
            add_edge(graph, node_id, near_sidewalk, "access", ["walk", "bike", "scooter"], "building_access")

    #add parking access points and connect them to roads and sidewalks
    for row in data:
        if row["feature_type"] != "parking_access":
            continue
        x_coord, y_coord = lonlat_to_web(row["longitude"], row["latitude"])
        node_id = row["part_id"]
        parking_id = row["feature_id"]
        add_graph_node(
            graph,
            node_id,
            row["longitude"],
            row["latitude"],
            x_coord,
            y_coord,
            "parking",
            parking_id,
        )
        if parking_id not in graph["parking_lots"]:
            graph["parking_lots"][parking_id] = []
        graph["parking_lots"][parking_id].append(node_id)
        near_road, road_distance = nearest_node(graph, x_coord, y_coord, ["road"])
        if near_road is not None and road_distance <= PARKING_ROAD_CONNECT_DISTANCE:
            add_edge(graph, node_id, near_road, "parking_drive", ["car"], "parking_drive")

        near_sidewalk, sidewalk_distance = nearest_node(graph, x_coord, y_coord, ["sidewalk"])
        if near_sidewalk is not None and sidewalk_distance <= PARKING_SIDEWALK_CONNECT_DISTANCE:
            add_edge(graph, node_id, near_sidewalk, "parking_walk", ["walk", "bike", "scooter"], "parking_walk")

    #connect close sidewalk points together
    connect_close_nodes(
        graph,
        "sidewalk",
        SIDEWALK_GAP_CONNECT_DISTANCE,
        "sidewalk_gap",
        ["walk", "bike", "scooter"],
    )

    #connect parking access points to nearby road nodes after everything is loaded
    for parking_id, parking_nodes in graph["parking_lots"].items():
        for parking_node in parking_nodes:
            parking = graph["nodes"][parking_node]
            near_road, road_distance = nearest_node(graph, parking["x"], parking["y"], ["road"])
            if near_road is not None and road_distance <= 150.0:
                add_edge(graph, parking_node, near_road, "parking_drive", ["car"], "parking_drive")
            near_sidewalk, sidewalk_distance = nearest_node(graph, parking["x"], parking["y"], ["sidewalk"])
            if near_sidewalk is not None and sidewalk_distance <= PARKING_SIDEWALK_CONNECT_DISTANCE:
                add_edge(graph, parking_node, near_sidewalk, "parking_walk", ["walk", "bike", "scooter"], "parking_walk")

    #connect sidewalks to roads at intersections so people can cross roads
    road_nodes = [node_id for node_id, node in graph["nodes"].items() if node["type"] == "road"]
    sidewalk_nodes = [node_id for node_id, node in graph["nodes"].items() if node["type"] == "sidewalk"]
    #loop through road and sidewalk points to make crossing connections, cause we love loops
    for road_node in road_nodes:
        road = graph["nodes"][road_node]
        for sidewalk_node in sidewalk_nodes:
            sidewalk = graph["nodes"][sidewalk_node]
            distance_m = xy_distance([road["x"], road["y"]], [sidewalk["x"], sidewalk["y"]])
            if distance_m <= CROSSING_CONNECT_DISTANCE:
                add_edge(graph, road_node, sidewalk_node, "crossing", ["walk", "bike", "scooter"], "road_crossing")
    return graph


#Function for getting the edge cost depending on mode and distance/time setting
def edge_cost(edge, mode, optimize_by):
    distance_m = edge["distance_m"]
    if optimize_by == "distance":
        return distance_m
    #time based weights
    if mode == "scooter":
        speed_mph = scooter_speed_from_distance(distance_m)
    else:
        speed_mph = SPEEDS_MPH[mode]
    speed_mps = mph_to_mps(speed_mph)
    time_seconds = distance_m / speed_mps
    #cars lose time at intersections because they slow down, stop, or turn
    if mode == "car" and edge["path_type"] == "road" and edge.get("to_intersection", False):
        time_seconds += CAR_INTERSECTION_DELAY
    return time_seconds


#Dijkstra shortest path function
def dijkstra(graph, start_node, end_node, mode, optimize_by="time"):
    if start_node not in graph["nodes"]:
        raise ValueError("Start node was not found in graph: " + start_node)
    if end_node not in graph["nodes"]:
        raise ValueError("End node was not found in graph: " + end_node)
    distances = {}
    previous = {}
    visited = set()
    #start every distance at infinity
    for node_id in graph["nodes"]:
        distances[node_id] = float("inf")
    distances[start_node] = 0.0
    heap = [[0.0, start_node]]
    #start of the main Dijkstra loop, cause we love loops
    while len(heap) > 0:
        current_cost, current_node = heapq.heappop(heap)
        if current_node in visited:
            continue
        visited.add(current_node)
        if current_node == end_node:
            break
        #loop through the places this node can go next
        for edge in graph["adj"][current_node]:
            if mode not in edge["modes"]:
                continue
            next_node = edge["to"]
            new_cost = current_cost + edge_cost(edge, mode, optimize_by)
            if new_cost < distances[next_node]:
                distances[next_node] = new_cost
                previous[next_node] = current_node
                heapq.heappush(heap, [new_cost, next_node])
    if distances[end_node] == float("inf"):
        return None

    #rebuild the path by walking backward through previous nodes
    path = []
    current = end_node
    while current != start_node:
        path.append(current)
        current = previous[current]
    path.append(start_node)
    path.reverse()
    return path, distances[end_node]


#Function for getting path distance even if the route was solved by time
def path_distance(graph, path):
    total_distance = 0.0
    #loop through the path one edge at a time, cause we love loops
    for i in range(len(path) - 1):
        node_a = path[i]
        node_b = path[i + 1]
        for edge in graph["adj"][node_a]:
            if edge["to"] == node_b:
                total_distance += edge["distance_m"]
                break
    return total_distance


#Function for combining route pieces into one route
def combine_route_pieces(route_pieces):
    final_path = []
    total_cost = 0.0
    #loop through the route pieces and stick them together
    for piece in route_pieces:
        if piece is None:
            return None
        path, cost = piece
        total_cost += cost
        if len(final_path) == 0:
            final_path.extend(path)
        else:
            final_path.extend(path[1:])
    return final_path, total_cost


#Function for solving walking, biking, and scooters
def solve_simple_mode(graph, start_id, end_id, mode, optimize_by="time"):
    return dijkstra(graph, start_id, end_id, mode, optimize_by)


#Function for solving car route, which has to do walk -> drive -> walk
def solve_car_route(graph, start_id, end_id, car_parked_id, optimize_by="time"):
    if car_parked_id not in graph["parking_lots"]:
        raise ValueError("Parking lot was not found: " + car_parked_id)
    best_route = None
    best_cost = float("inf")
    best_parking = None
    start_parking_nodes = graph["parking_lots"][car_parked_id]
    #try every access point of the starting parking lot, cause we love loops
    for start_parking_node in start_parking_nodes:
        walk_to_car = dijkstra(graph, start_id, start_parking_node, "walk", optimize_by)
        if walk_to_car is None:
            continue
        #try every destination parking access point
        #try every destination parking access point
        for parking_id, parking_nodes in graph["parking_lots"].items():
            for end_parking_node in parking_nodes:
                drive_route = dijkstra(graph, start_parking_node, end_parking_node, "car", optimize_by)
                walk_to_end = dijkstra(graph, end_parking_node, end_id, "walk", optimize_by)
                route = combine_route_pieces([walk_to_car, drive_route, walk_to_end])
                if route is None:
                    continue
                path, cost = route
                if cost < best_cost:
                    best_cost = cost
                    best_route = path
                    best_parking = parking_id
    if best_route is None:
        return None
    return best_route, best_cost, best_parking


#Main route solving function
def solve_route(graph, start_id, end_id, mode, optimize_by="time", car_parked_id=None):
    if mode == "car":
        return solve_car_route(graph, start_id, end_id, car_parked_id, optimize_by)
    return solve_simple_mode(graph, start_id, end_id, mode, optimize_by)


#Function for listing valid start/end locations
def location_options(graph):
    return graph["locations"]


#Function for listing parking lot choices
def parking_options(graph):
    return sorted(graph["parking_lots"].keys())