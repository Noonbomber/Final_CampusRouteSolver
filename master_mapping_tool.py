# Author: Landon Schultz
# Date: 5-4-26

import csv
from pathlib import Path

import contextily as cx
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons
from pyproj import Transformer

from map_viewer import add_scroll_zoom
from settings import CAMPUS_BOUNDS_LONLAT, MAP_ZOOM


### Master mapping tool for the campus route solver
#This combines the different map drawing scripts into one program
#It can place roads, sidewalks, parking lot access points, and places/POIs


BOUNDS_FILE = Path("data/picked_map_bounds.csv")
MASTER_FILE = Path("data/master_map_data.csv")


#Function for loading the exact map bounds
def load_map_bounds():

    if not BOUNDS_FILE.exists():
        return CAMPUS_BOUNDS_LONLAT

    with BOUNDS_FILE.open("r", newline="") as file:
        reader = csv.DictReader(file)
        row = next(reader)

    return (
        float(row["west"]),
        float(row["south"]),
        float(row["east"]),
        float(row["north"]),
    )


#Function for downloading map tiles
def get_basemap():

    west, south, east, north = load_map_bounds()

    print("Downloading map tiles. This may take a moment...")

    tile_sources = [
        cx.providers.OpenStreetMap.Mapnik,
        cx.providers.CartoDB.Positron,
    ]

    basemap_image = None
    basemap_extent = None
    last_error = None

    #loop through tile sources until one works
    for tile_source in tile_sources:
        try:
            basemap_image, basemap_extent = cx.bounds2img(
                west,
                south,
                east,
                north,
                zoom=MAP_ZOOM,
                source=tile_source,
                ll=True,
                use_cache=False,
                n_connections=1,
            )
            break
        except Exception as error:
            last_error = error
            print("Tile source failed:", tile_source["name"])

    if basemap_image is None:
        raise RuntimeError("Could not download campus map tiles.") from last_error

    return basemap_image, basemap_extent


#Function for writing the master csv header
def write_master_header():

    MASTER_FILE.parent.mkdir(exist_ok=True)

    with MASTER_FILE.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "feature_type",
            "feature_id",
            "feature_name",
            "part_id",
            "point_order",
            "point_kind",
            "longitude",
            "latitude",
        ])


#Function for appending a row to the master file
def append_master_row(feature_type, feature_id, feature_name, part_id, point_order, point_kind, lon, lat):

    if not MASTER_FILE.exists():
        write_master_header()

    with MASTER_FILE.open("a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            feature_type,
            feature_id,
            feature_name,
            part_id,
            point_order,
            point_kind,
            lon,
            lat,
        ])


#Function for loading the master data
def load_master_data():

    if not MASTER_FILE.exists():
        write_master_header()

    data = []

    with MASTER_FILE.open("r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            row["longitude"] = float(row["longitude"])
            row["latitude"] = float(row["latitude"])
            row["point_order"] = int(row["point_order"])
            data.append(row)

    return data


#Function for getting a new feature number
def next_feature_id(data, feature_type):

    used_ids = set()

    for row in data:
        if row["feature_type"] == feature_type:
            used_ids.add(row["feature_id"])

    return feature_type + "_" + str(len(used_ids) + 1).zfill(3)


#Function for plotting line features
def plot_line_features(ax, data, feature_type, lonlat_to_web, color, linewidth, alpha, zorder):

    features = {}

    for row in data:
        if row["feature_type"] == feature_type:
            feature_id = row["feature_id"]

            if feature_id not in features:
                features[feature_id] = []

            features[feature_id].append(row)

    for feature_id, points in features.items():
        points.sort(key=lambda point: point["point_order"])
        x_values = []
        y_values = []

        for point in points:
            x_coord, y_coord = lonlat_to_web.transform(point["longitude"], point["latitude"])
            x_values.append(x_coord)
            y_values.append(y_coord)

        ax.plot(
            x_values,
            y_values,
            color=color,
            linewidth=linewidth,
            alpha=alpha,
            zorder=zorder,
        )


#Function for plotting point features
def plot_point_features(ax, data, feature_type, lonlat_to_web, color, size, marker, zorder):

    for row in data:
        if row["feature_type"] == feature_type:
            x_coord, y_coord = lonlat_to_web.transform(row["longitude"], row["latitude"])
            ax.scatter(
                x_coord,
                y_coord,
                s=size,
                color=color,
                marker=marker,
                edgecolor="white",
                zorder=zorder,
            )


#Main function
def main():

    if not MASTER_FILE.exists():
        write_master_header()

    data = load_master_data()

    lonlat_to_web = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    web_to_lonlat = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    west, south, east, north = load_map_bounds()
    west_x, south_y = lonlat_to_web.transform(west, south)
    east_x, north_y = lonlat_to_web.transform(east, north)

    basemap_image, basemap_extent = get_basemap()

    current_mode = ["Road"]
    current_points_web = []
    current_points_lonlat = []
    current_artists = []
    current_line = [None]

    fig = plt.figure(figsize=(18, 10))
    map_ax = fig.add_axes([0.16, 0.02, 0.83, 0.94])
    radio_ax = fig.add_axes([0.02, 0.55, 0.12, 0.22])

    map_ax.imshow(basemap_image, extent=basemap_extent)
    map_ax.set_xlim(west_x, east_x)
    map_ax.set_ylim(south_y, north_y)
    map_ax.set_axis_off()

    #radio buttons for choosing what is being placed
    radio_buttons = RadioButtons(
        radio_ax,
        ["Road", "Sidewalk", "Parking", "Place"],
        active=0,
    )

    #draw already collected data
    plot_line_features(map_ax, data, "sidewalk", lonlat_to_web, "limegreen", 1.3, 0.70, 3)
    plot_line_features(map_ax, data, "road", lonlat_to_web, "dodgerblue", 2.2, 0.80, 4)
    plot_point_features(map_ax, data, "road_intersection", lonlat_to_web, "yellow", 38, "o", 6)
    plot_point_features(map_ax, data, "parking_access", lonlat_to_web, "gold", 38, "s", 7)
    plot_point_features(map_ax, data, "building", lonlat_to_web, "crimson", 34, "o", 8)
    plot_point_features(map_ax, data, "poi", lonlat_to_web, "purple", 42, "o", 8)

    map_ax.set_title("Master Campus Mapping Tool")
    add_scroll_zoom(fig, map_ax)

    #Function for changing the selected mode
    def change_mode(label):
        current_mode[0] = label
        map_ax.set_title("Master Campus Mapping Tool - Current Mode: " + label)
        fig.canvas.draw_idle()

    radio_buttons.on_clicked(change_mode)

    #Function for redrawing the current unsaved line
    def redraw_current_line(color):

        if current_line[0] is not None:
            current_line[0].remove()
            current_line[0] = None

        if len(current_points_web) >= 2:
            x_values = [point[0] for point in current_points_web]
            y_values = [point[1] for point in current_points_web]
            current_line[0], = map_ax.plot(x_values, y_values, color=color, linewidth=3, zorder=10)

        fig.canvas.draw_idle()

    #Function for clearing the current unsaved points
    def clear_current_points():

        current_points_web.clear()
        current_points_lonlat.clear()

        for artist in current_artists:
            artist.remove()

        current_artists.clear()

        if current_line[0] is not None:
            current_line[0].remove()
            current_line[0] = None

        fig.canvas.draw_idle()

    #Function for clicking on the map
    def on_click(event):

        if event.inaxes != map_ax or event.xdata is None or event.ydata is None:
            return

        #right click places points so left click can be used for panning
        if event.button != 3:
            return

        lon, lat = web_to_lonlat.transform(event.xdata, event.ydata)
        mode = current_mode[0]

        #road and sidewalk modes are line based
        if mode in ["Road", "Sidewalk"]:
            if event.key == "control":
                point_kind = "curve"
                marker = "x"
            else:
                point_kind = "intersection"
                marker = "o"

            current_points_web.append([event.xdata, event.ydata])
            current_points_lonlat.append([lon, lat, point_kind])

            color = "dodgerblue" if mode == "Road" else "limegreen"

            point = map_ax.scatter(
                event.xdata,
                event.ydata,
                s=44,
                color=color,
                marker=marker,
                edgecolor="white",
                zorder=11,
            )
            current_artists.append(point)
            redraw_current_line(color)

        #parking mode is point based and saves right away
        elif mode == "Parking":
            feature_id = next_feature_id(data, "parking_access")
            append_master_row("parking_access", feature_id, feature_id, feature_id, 0, "access", lon, lat)

            row = {
                "feature_type": "parking_access",
                "feature_id": feature_id,
                "feature_name": feature_id,
                "part_id": feature_id,
                "point_order": 0,
                "point_kind": "access",
                "longitude": lon,
                "latitude": lat,
            }
            data.append(row)

            map_ax.scatter(event.xdata, event.ydata, s=50, color="gold", marker="s", edgecolor="white", zorder=11)
            print("Saved parking access:", feature_id, lon, lat)
            fig.canvas.draw_idle()

        #place mode is point based and saves right away
        elif mode == "Place":
            feature_id = next_feature_id(data, "poi")
            append_master_row("poi", feature_id, feature_id, "", 0, "point", lon, lat)

            row = {
                "feature_type": "poi",
                "feature_id": feature_id,
                "feature_name": feature_id,
                "part_id": "",
                "point_order": 0,
                "point_kind": "point",
                "longitude": lon,
                "latitude": lat,
            }
            data.append(row)

            map_ax.scatter(event.xdata, event.ydata, s=50, color="purple", edgecolor="white", zorder=11)
            print("Saved POI:", feature_id, lon, lat)
            fig.canvas.draw_idle()

    #Function for keyboard controls
    def on_key(event):

        mode = current_mode[0]

        #enter saves current road or sidewalk line
        if event.key == "enter":
            if mode not in ["Road", "Sidewalk"]:
                return

            if len(current_points_lonlat) < 2:
                print("Need at least two points before saving a line.")
                return

            feature_type = "road" if mode == "Road" else "sidewalk"
            feature_id = next_feature_id(data, feature_type)

            for i, point in enumerate(current_points_lonlat):
                append_master_row(feature_type, feature_id, "", feature_id, i, point[2], point[0], point[1])

                data.append({
                    "feature_type": feature_type,
                    "feature_id": feature_id,
                    "feature_name": "",
                    "part_id": feature_id,
                    "point_order": i,
                    "point_kind": point[2],
                    "longitude": point[0],
                    "latitude": point[1],
                })

            color = "dodgerblue" if mode == "Road" else "limegreen"
            x_values = [point[0] for point in current_points_web]
            y_values = [point[1] for point in current_points_web]
            map_ax.plot(x_values, y_values, color=color, linewidth=2, alpha=0.65, zorder=5)
            clear_current_points()
            print("Saved", feature_type, "line:", feature_id)
            return

        #backspace removes the last unsaved line point
        if event.key == "backspace":
            if len(current_points_lonlat) == 0:
                print("No current points to remove.")
                return

            current_points_lonlat.pop()
            current_points_web.pop()
            artist = current_artists.pop()
            artist.remove()

            color = "dodgerblue" if mode == "Road" else "limegreen"
            redraw_current_line(color)
            print("Removed last unsaved point.")
            return

        #c clears current unsaved points
        if event.key == "c":
            clear_current_points()
            print("Cleared current unsaved points.")
            return

        #q closes the tool
        if event.key == "q":
            print("Closing master mapping tool.")
            plt.close(fig)
            return

    fig.canvas.mpl_connect("button_press_event", on_click)
    fig.canvas.mpl_connect("key_press_event", on_key)

    print("----- Master Mapping Tool Instructions -----")
    print("Choose the current data type with the radio buttons on the left.")
    print("Right click: place a point")
    print("Ctrl + right click: curve point for road/sidewalk lines")
    print("Enter: save current road/sidewalk line")
    print("Backspace: remove last unsaved line point")
    print("c: clear current unsaved line")
    print("q: quit")
    print("Master file:", MASTER_FILE.resolve())
    print()

    plt.show()


if __name__ == "__main__":
    main()
