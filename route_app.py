# Author: Landon Schultz
# Date: 5-5-26

import contextily as cx
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from pyproj import Transformer

from map_viewer import add_scroll_zoom, load_map_bounds, load_master_data, plot_line_features, plot_point_features
from numerical_methods import interpolation_error_analysis, scooter_walk_break_even
from route_solver import (
    build_campus_graph,
    location_options,
    parking_options,
    path_distance,
    solve_route,
)
from settings import MAP_ZOOM, SPEEDS_MPH


#Main app file for the campus route solver
#This is the one to actually run for the final project


#Function to download the background campus map tiles
def get_basemap():
    west, south, east, north = load_map_bounds()
    print("Downloading map tiles. This may take a moment...")
    basemap_image, basemap_extent = cx.bounds2img(
        west,
        south,
        east,
        north,
        zoom=MAP_ZOOM,
        source=cx.providers.OpenStreetMap.Mapnik,
        ll=True,
        use_cache=False,
        n_connections=1,
    )
    return basemap_image, basemap_extent


#Function to make seconds print nicer in the output
def format_time(seconds):
    total_seconds = int(round(seconds))
    minutes = total_seconds // 60
    leftover_seconds = total_seconds % 60
    return f"{minutes} min {leftover_seconds} sec"


#meters to miles conversion for final outputs
def meters_to_miles(distance_m):
    return distance_m / 1609.344


#Function to make the distance output look better
def format_distance(distance_m):
    return f"{meters_to_miles(distance_m):.3f} miles"


#Function for plotting the path that dijkstra spits out
def plot_route(ax, graph, path, color, label):
    x_values = []
    y_values = []
    #loop through the path and grab the coordinates, cause we love loops
    for node_id in path:
        node = graph["nodes"][node_id]
        x_values.append(node["x"])
        y_values.append(node["y"])

    ax.plot(
        x_values,
        y_values,
        color=color,
        linewidth=4,
        alpha=0.95,
        label=label,
        zorder=20,
    )


#Function to print all the location options to terminal
#This is mostly for checking ids if something gets weird
def print_options(graph):
    print("----- Valid Start/End Locations -----")
    #loop through the locations so I can see the real ids
    for location_id, name in sorted(location_options(graph).items()):
        print(location_id, "-", name)
    print()
    print("----- Parking Lot Choices For Car Mode -----")
    #loop through parking choices too
    for parking_id in parking_options(graph):
        print(parking_id)
    print()


#Function to draw labels for buildings and parking lots
def plot_big_labels(ax, graph):
    #loop through the important points and label them on the map
    for node_id, node in graph["nodes"].items():
        if node["type"] not in ["building", "poi", "parking"]:
            continue

        if node["type"] == "parking":
            label = node["name"]
            color = "gold"
            fontsize = 7
        else:
            label = node["name"]
            color = "white"
            fontsize = 8

        ax.annotate(
            label,
            (node["x"], node["y"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=fontsize,
            color="black",
            bbox={"boxstyle": "round,pad=0.25", "fc": color, "alpha": 0.82},
            zorder=25,
        )


#Function for making the little selector button groups
#I used buttons so the user cannot type some random bad node id
def make_selector(fig, x, y, label, options, start_index=0, display_names=None):
    if display_names is None:
        display_names = {}
    state = {
        "index": start_index,
        "options": options,
    }

    label_ax = fig.add_axes([x, y + 0.035, 0.18, 0.025])
    label_ax.axis("off")
    label_text = label_ax.text(0, 0.5, label, fontsize=8, va="center")

    value_ax = fig.add_axes([x + 0.035, y, 0.11, 0.035])
    value_ax.axis("off")
    value_text = value_ax.text(
        0.5,
        0.5,
        display_names.get(options[start_index], options[start_index]),
        fontsize=7,
        ha="center",
        va="center",
        bbox={"boxstyle": "round,pad=0.20", "fc": "white", "alpha": 0.9},
    )

    prev_ax = fig.add_axes([x, y, 0.03, 0.035])
    next_ax = fig.add_axes([x + 0.15, y, 0.03, 0.035])
    prev_button = Button(prev_ax, "<")
    next_button = Button(next_ax, ">")

    def update_text():
        current_option = state["options"][state["index"]]
        value_text.set_text(display_names.get(current_option, current_option))
        fig.canvas.draw_idle()

    #go backward through the options
    def previous(event):
        state["index"] = (state["index"] - 1) % len(state["options"])
        update_text()

    #go forward through the options
    def next_value(event):
        state["index"] = (state["index"] + 1) % len(state["options"])
        update_text()

    prev_button.on_clicked(previous)
    next_button.on_clicked(next_value)

    def get_value():
        return state["options"][state["index"]]

    return get_value, [prev_button, next_button], label_text, value_text


#Function for solving one route from the selector values
def solve_route_from_selectors(graph, route_selectors):
    mode = route_selectors["mode"]()
    optimize_by = route_selectors["optimize"]()
    start_id = route_selectors["start"]()
    end_id = route_selectors["end"]()
    car_parked_id = route_selectors["parking"]()
    result = solve_route(graph, start_id, end_id, mode, optimize_by, car_parked_id)
    if result is None:
        return None
    if mode == "car":
        path, cost, best_parking = result
    else:
        path, cost = result
        best_parking = ""
    distance_m = path_distance(graph, path)
    return {
        "mode": mode,
        "optimize_by": optimize_by,
        "start": start_id,
        "end": end_id,
        "parking": car_parked_id,
        "destination_parking": best_parking,
        "path": path,
        "cost": cost,
        "distance_m": distance_m,
    }


#Function for making the result text box and terminal output
def route_summary(title, result):
    if result is None:
        return title + "\nNo route found."
    if result["optimize_by"] == "time":
        cost_text = format_time(result["cost"])
    else:
        cost_text = format_distance(result["cost"])

    text = (
        title + "\n"
        + "Mode: " + result["mode"] + "\n"
        + "Start: " + result["start"] + "\n"
        + "End: " + result["end"] + "\n"
        + "Cost: " + cost_text + "\n"
        + "Distance: " + format_distance(result["distance_m"])
    )
    if result["mode"] == "car":
        text += "\nParked at: " + result["parking"]
        text += "\nDestination lot: " + result["destination_parking"]
    return text


#Main function for the UI
def main():
    #build the graph one time when the app opens
    graph = build_campus_graph()
    data = load_master_data()
    print_options(graph)

    lonlat_to_web = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

    west, south, east, north = load_map_bounds()
    west_x, south_y = lonlat_to_web.transform(west, south)
    east_x, north_y = lonlat_to_web.transform(east, north)

    basemap_image, basemap_extent = get_basemap()

    location_ids = sorted(location_options(graph).keys())
    location_names = location_options(graph)
    parking_ids = parking_options(graph)
    parking_names = {}
    #loop through parking ids to make the selector names
    for parking_id in parking_ids:
        parking_names[parking_id] = parking_id

    mode_options = ["walk", "bike", "scooter", "car"]
    optimize_options = ["time", "distance"]

    fig = plt.figure(figsize=(19, 10))
    map_ax = fig.add_axes([0.28, 0.04, 0.70, 0.92])

    map_ax.imshow(basemap_image, extent=basemap_extent)
    plot_line_features(map_ax, data, "sidewalk", lonlat_to_web, "limegreen", 1.0, 0.42, 3)
    plot_line_features(map_ax, data, "road", lonlat_to_web, "dodgerblue", 2.0, 0.65, 4)
    plot_point_features(map_ax, data, "road_intersection", lonlat_to_web, "yellow", 32, "o", 6)
    plot_point_features(map_ax, data, "parking_access", lonlat_to_web, "gold", 36, "s", 7)
    plot_point_features(map_ax, data, "building", lonlat_to_web, "crimson", 36, "o", 8, False)
    plot_point_features(map_ax, data, "poi", lonlat_to_web, "purple", 44, "o", 8, False)
    plot_big_labels(map_ax, graph)

    map_ax.set_xlim(west_x, east_x)
    map_ax.set_ylim(south_y, north_y)
    map_ax.set_axis_off()
    map_ax.set_title("Campus Route Solver")
    add_scroll_zoom(fig, map_ax)

    all_buttons = []
    route1 = {}
    route2 = {}

    ### Route 1 controls
    title1_ax = fig.add_axes([0.02, 0.91, 0.22, 0.035])
    title1_ax.axis("off")
    title1_ax.text(0, 0.5, "Route 1", fontsize=12, fontweight="bold", va="center")

    route1["mode"], buttons, _, _ = make_selector(fig, 0.02, 0.85, "Mode", mode_options, 0)
    all_buttons.extend(buttons)
    route1["optimize"], buttons, _, _ = make_selector(fig, 0.02, 0.78, "Optimize", optimize_options, 0)
    all_buttons.extend(buttons)
    route1["start"], buttons, _, _ = make_selector(fig, 0.02, 0.71, "Start", location_ids, location_ids.index("library") if "library" in location_ids else 0, location_names)
    all_buttons.extend(buttons)
    route1["end"], buttons, _, _ = make_selector(fig, 0.02, 0.64, "End", location_ids, location_ids.index("student_union") if "student_union" in location_ids else 0, location_names)
    all_buttons.extend(buttons)
    route1["parking"], buttons, _, _ = make_selector(fig, 0.02, 0.57, "Car Parked", parking_ids, 0, parking_names)
    all_buttons.extend(buttons)

    ### Route 2 controls
    title2_ax = fig.add_axes([0.02, 0.48, 0.22, 0.035])
    title2_ax.axis("off")
    title2_ax.text(0, 0.5, "Route 2", fontsize=12, fontweight="bold", va="center")

    route2["mode"], buttons, _, _ = make_selector(fig, 0.02, 0.42, "Mode", mode_options, 3)
    all_buttons.extend(buttons)
    route2["optimize"], buttons, _, _ = make_selector(fig, 0.02, 0.35, "Optimize", optimize_options, 0)
    all_buttons.extend(buttons)
    route2["start"], buttons, _, _ = make_selector(fig, 0.02, 0.28, "Start", location_ids, location_ids.index("library") if "library" in location_ids else 0, location_names)
    all_buttons.extend(buttons)
    route2["end"], buttons, _, _ = make_selector(fig, 0.02, 0.21, "End", location_ids, location_ids.index("student_union") if "student_union" in location_ids else 0, location_names)
    all_buttons.extend(buttons)
    route2["parking"], buttons, _, _ = make_selector(fig, 0.02, 0.14, "Car Parked", parking_ids, 0, parking_names)
    all_buttons.extend(buttons)

    solve1_ax = fig.add_axes([0.02, 0.075, 0.07, 0.045])
    solve2_ax = fig.add_axes([0.10, 0.075, 0.07, 0.045])
    compare_ax = fig.add_axes([0.18, 0.075, 0.07, 0.045])
    solve1_button = Button(solve1_ax, "Solve 1")
    solve2_button = Button(solve2_ax, "Solve 2")
    compare_button = Button(compare_ax, "Compare")
    all_buttons.extend([solve1_button, solve2_button, compare_button])

    info_ax = fig.add_axes([0.02, 0.005, 0.24, 0.06])
    info_ax.axis("off")
    info_text = info_ax.text(0, 1, "Use < and > to select options.", va="top", fontsize=8)

    route_lines = []

    #Function for clearing old route lines
    def clear_routes():
        #loop until all the old route lines are gone, cause we love loops
        while len(route_lines) > 0:
            line = route_lines.pop()
            line.remove()

    #Function for drawing one route on the map
    def draw_result(result, color, label):
        before_lines = len(map_ax.lines)
        plot_route(map_ax, graph, result["path"], color, label)
        route_lines.extend(map_ax.lines[before_lines:])

    #Function for solving route 1
    def solve_one(event):
        clear_routes()
        result = solve_route_from_selectors(graph, route1)
        if result is not None:
            draw_result(result, "crimson", "Route 1")
        info_text.set_text(route_summary("Route 1", result))
        print(route_summary("Route 1", result))
        print()
        fig.canvas.draw_idle()

    #Function for solving route 2
    def solve_two(event):
        clear_routes()
        result = solve_route_from_selectors(graph, route2)
        if result is not None:
            draw_result(result, "black", "Route 2")
        info_text.set_text(route_summary("Route 2", result))
        print(route_summary("Route 2", result))
        print()
        fig.canvas.draw_idle()

    #Function for comparing both selected routes, this is one of the main project features
    def compare_routes(event):
        clear_routes()
        result1 = solve_route_from_selectors(graph, route1)
        result2 = solve_route_from_selectors(graph, route2)
        if result1 is not None:
            draw_result(result1, "crimson", "Route 1")
        if result2 is not None:
            draw_result(result2, "black", "Route 2")
        lines = ["Route Comparison"]
        #loop through both routes and build the comparison text
        for title, result in [["Route 1", result1], ["Route 2", result2]]:
            if result is None:
                lines.append(title + ": no route")
            else:
                if result["optimize_by"] == "time":
                    cost_text = format_time(result["cost"])
                else:
                    cost_text = format_distance(result["cost"])

                lines.append(
                    title + ": "
                    + result["mode"]
                    + ", "
                    + cost_text
                    + ", "
                    + format_distance(result["distance_m"])
                )
        print("----- Route Comparison -----")
        #loop through the comparison lines for the terminal
        for line in lines:
            print(line)

        print()
        #print the interpolation and bisection bits from numerical_methods.py too
        print("----- Interpolation Error Analysis -----")
        #loop through the interpolation checks from the numerical methods file
        for row in interpolation_error_analysis():
            print("Distance:", row[0], "m | interp:", round(row[1], 2), "mph | direct:", round(row[2], 2), "mph | error:", round(row[3], 2), "%")

        walk_speed_mps = SPEEDS_MPH["walk"] * 1609.344 / 3600
        break_even_distance, iterations = scooter_walk_break_even(walk_speed_mps)
        print()
        print("Scooter/walk break-even distance:", round(meters_to_miles(break_even_distance), 3), "miles")
        print("Bisection iterations:", iterations)
        print()

        info_text.set_text("\n".join(lines))
        map_ax.legend(loc="lower right")
        fig.canvas.draw_idle()

    solve1_button.on_clicked(solve_one)
    solve2_button.on_clicked(solve_two)
    compare_button.on_clicked(compare_routes)

    print("----- UI Instructions -----")
    print("Use the < and > buttons to choose mode, optimization, start, end, and parking.")
    print("Route 1 and Route 2 can be completely different trips.")
    print("Click Solve 1, Solve 2, or Compare.")
    print("All distances shown in the UI are in miles.")
    print()

    plt.show()


if __name__ == "__main__":
    main()