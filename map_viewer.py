# Author: Landon Schultz
# Date: 5-3-26

import csv
from pathlib import Path

import contextily as cx
import matplotlib.pyplot as plt
from pyproj import Transformer

from settings import CAMPUS_BOUNDS_LONLAT, MAP_ZOOM

#This is not the route solver, it is just for checking the data on the map
MASTER_FILE = Path("data/master_map_data.csv")


#Function to allow mouse wheel zoom in matplotlib
def add_scroll_zoom(fig, ax, base_scale=1.35):
    #this function runs every time the mouse wheel scrolls
    def zoom(event):
        #ignore scrolls that are not on the map
        if event.inaxes != ax or event.xdata is None or event.ydata is None:
            return
        #get current map limits
        current_xlim = ax.get_xlim()
        current_ylim = ax.get_ylim()
        current_width = current_xlim[1] - current_xlim[0]
        current_height = current_ylim[1] - current_ylim[0]
        #scroll up zooms in and scroll down zooms out
        if event.button == "up":
            scale_factor = 1 / base_scale
        elif event.button == "down":
            scale_factor = base_scale
        else:
            return
        #new width and height after zooming
        new_width = current_width * scale_factor
        new_height = current_height * scale_factor
        #keeps the zoom centered on the mouse
        x_relative = (current_xlim[1] - event.xdata) / current_width
        y_relative = (current_ylim[1] - event.ydata) / current_height

        ax.set_xlim(
            event.xdata - new_width * (1 - x_relative),
            event.xdata + new_width * x_relative,
        )
        ax.set_ylim(
            event.ydata - new_height * (1 - y_relative),
            event.ydata + new_height * y_relative,
        )
        fig.canvas.draw_idle()
    fig.canvas.mpl_connect("scroll_event", zoom)


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


#Function for downloading the background map tiles
def get_basemap():
    west, south, east, north = load_map_bounds()
    print("Downloading map tiles. This may take a moment...")
    #try two different tile sources in case one fails
    tile_sources = [
        cx.providers.OpenStreetMap.Mapnik,
        cx.providers.CartoDB.Positron,
    ]

    basemap_image = None
    basemap_extent = None
    last_error = None
    #loop through tile sources until one works, cause we love loops
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
    #error handling if no tile source works
    if basemap_image is None:
        raise RuntimeError("Could not download the campus map tiles.") from last_error
    return basemap_image, basemap_extent


#Function for loading the master map data
def load_master_data():
    if not MASTER_FILE.exists():
        raise FileNotFoundError("Could not find data/master_map_data.csv")
    data = []
    with MASTER_FILE.open("r", newline="") as file:
        reader = csv.DictReader(file)
        #loop through the csv rows, cause we love loops
        for row in reader:
            row["longitude"] = float(row["longitude"])
            row["latitude"] = float(row["latitude"])
            row["point_order"] = int(row["point_order"])
            data.append(row)
    return data


#Function for plotting roads or sidewalks
#The csv stores every clicked point as its own row, so this groups them back up
def plot_line_features(ax, data, feature_type, lonlat_to_web, color, linewidth, alpha, zorder):
    #group all the points by feature id
    features = {}
    #loop through the data and group the matching line type
    for row in data:
        if row["feature_type"] == feature_type:
            feature_id = row["feature_id"]

            if feature_id not in features:
                features[feature_id] = []

            features[feature_id].append(row)
    #plot each feature after sorting the points by point order, cause we love loops
    for feature_id, points in features.items():
        points.sort(key=lambda point: point["point_order"])
        x_values = []
        y_values = []
        #loop through the points for this one line
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


#Function for plotting point features like buildings and parking
def plot_point_features(ax, data, feature_type, lonlat_to_web, color, size, marker, zorder, show_labels=False):
    #loop through points and only plot the type that was asked for
    for row in data:
        if row["feature_type"] != feature_type:
            continue
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
        if show_labels:
            label = row["feature_name"] if row["feature_name"] != "" else row["feature_id"]
            ax.annotate(
                label,
                (x_coord, y_coord),
                xytext=(4, 4),
                textcoords="offset points",
                fontsize=6,
                color="black",
                bbox={"boxstyle": "round,pad=0.15", "fc": "white", "alpha": 0.70},
                zorder=zorder + 1,
            )


#Function for plotting the whole map with all of my collected data
def plot_master_map(show_labels=True):
    #converts longitude/latitude into the map tile coordinate system
    lonlat_to_web = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    #get the bounds and convert them
    west, south, east, north = load_map_bounds()
    west_x, south_y = lonlat_to_web.transform(west, south)
    east_x, north_y = lonlat_to_web.transform(east, north)
    #load data and basemap
    data = load_master_data()
    basemap_image, basemap_extent = get_basemap()
    #create figure, made wider so the campus map fills the window better
    fig, ax = plt.subplots(figsize=(18, 10))
    fig.subplots_adjust(left=0.005, right=0.995, bottom=0.005, top=0.94)
    ax.imshow(basemap_image, extent=basemap_extent)
    #plot background network layers first
    plot_line_features(ax, data, "sidewalk", lonlat_to_web, "limegreen", 1.3, 0.70, 3)
    plot_line_features(ax, data, "road", lonlat_to_web, "dodgerblue", 2.2, 0.82, 4)
    #plot point layers second
    plot_point_features(ax, data, "road_intersection", lonlat_to_web, "yellow", 38, "o", 6)
    plot_point_features(ax, data, "parking_access", lonlat_to_web, "gold", 42, "s", 7)
    plot_point_features(ax, data, "building", lonlat_to_web, "crimson", 34, "o", 8, show_labels)
    plot_point_features(ax, data, "poi", lonlat_to_web, "purple", 42, "o", 8, show_labels)

    ax.set_title("Campus Master Map Data")
    ax.set_xlim(west_x, east_x)
    ax.set_ylim(south_y, north_y)
    ax.set_axis_off()
    add_scroll_zoom(fig, ax)

    print("----- Master Map Viewer -----")
    print("Rows loaded from master file:", len(data))
    print("Blue lines = roads")
    print("Green lines = sidewalks")
    print("Yellow dots = road intersections")
    print("Gold squares = parking access points")
    print("Red dots = buildings")
    print("Purple dots = POIs")
    print()
    print("Use the mouse wheel to zoom and the matplotlib toolbar to pan.")
    plt.show()


if __name__ == "__main__":
    plot_master_map()