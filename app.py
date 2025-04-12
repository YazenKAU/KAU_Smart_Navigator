import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
from geopy.distance import geodesic
from PIL import Image
from time import sleep

# === Paths ===
csv_folder = "AttributeTable"
img_folder = "Images/images"

# Load CSVs
buildings = pd.read_csv(os.path.join(csv_folder, "Building_Points.csv"))
routes = pd.read_csv(os.path.join(csv_folder, "All_Solved_Routes.csv"))
images = pd.read_csv(os.path.join(csv_folder, "Mapillary_Images.csv"))

# DEBUG (optional): Show available building columns
# st.write("📋 Columns in Building_Points.csv:", buildings.columns.tolist())

# Simulated GPS (for now)
user_lat = 21.4932
user_lon = 39.2465

st.set_page_config(page_title="KAU Smart Navigator", layout="wide")
st.title("📍 KAU Smart Navigator")

# === My Location Toggle
show_location = st.checkbox("📍 Show My Location")

# === Start / End Selectors
st.subheader("🧭 Choose Start and Destination")
col1, col2 = st.columns(2)
with col1:
    start = st.selectbox("Start Building", buildings["BuildingAr"])
with col2:
    end = st.selectbox("Destination Building", buildings["BuildingAr"])

# === Search
st.markdown("### 🔍 Search for a Building")
search_query = st.text_input("Type building name...")
if search_query:
    matches = buildings[buildings["BuildingAr"].str.contains(search_query, case=False)]
    if not matches.empty:
        st.success(f"✅ Found {len(matches)} result(s):")
        for _, row in matches.iterrows():
            st.markdown(f"- **{row['BuildingAr']}**")
            st.map(pd.DataFrame({"lat": [row["Latitude"]], "lon": [row["Longitude"]]}))
    else:
        st.warning("⚠️ No matching buildings found.")

# === From / To
from_row = buildings[buildings["BuildingAr"] == start].iloc[0]
to_row = buildings[buildings["BuildingAr"] == end].iloc[0]
from_id = from_row["ORIG_FID"]
to_id = to_row["ORIG_FID"]

# === Map
map_center = [21.4926, 39.2468]
if show_location:
    map_center = [user_lat, user_lon]

m = folium.Map(location=map_center, zoom_start=16)

# My Location Marker
if show_location:
    folium.CircleMarker(
        location=[user_lat, user_lon],
        radius=10,
        color="green",
        fill=True,
        fill_opacity=0.9,
        popup="📍 You Are Here"
    ).add_to(m)

# Building Markers
for _, row in buildings.iterrows():
    folium.Marker(
        location=[row["Latitude"], row["Longitude"]],
        popup=row["BuildingAr"],
        icon=folium.Icon(color="blue", icon="university", prefix="fa")
    ).add_to(m)

# === Draw Route
route_row = routes[
    ((routes["FromID"] == from_id) & (routes["ToID"] == to_id)) |
    ((routes["FromID"] == to_id) & (routes["ToID"] == from_id))
]

image_matches = []

if not route_row.empty:
    coords = [
        [from_row["Latitude"], from_row["Longitude"]],
        [to_row["Latitude"], to_row["Longitude"]]
    ]
    folium.PolyLine(
        locations=coords,
        color="red",
        weight=5,
        tooltip=f"Distance: {route_row['Length'].values[0]:.1f} m, Time: {route_row['TravelTime'].values[0]:.1f} min"
    ).add_to(m)
    st.success("✅ Route displayed!")

    # Filter photo points
    def is_nearby(lat, lon, threshold=0.05):
        pt = (lat, lon)
        return (
            geodesic(pt, coords[0]).meters < threshold * 1000 or
            geodesic(pt, coords[1]).meters < threshold * 1000
        )

    image_matches = images[images.apply(lambda row: is_nearby(row["lat"], row["lon"]), axis=1)]
    image_matches = image_matches.sort_values(by="id")
else:
    st.warning("⚠️ No route found between selected buildings.")

# === Map Viewer
st.markdown("### 🗺️ Campus Map")
st_data = st_folium(m, width=1200, height=500)

# === Image Viewer
if not image_matches.empty:
    st.markdown("### 🖼️ Visual Walkthrough")
    img_files = image_matches["photo_path"].apply(lambda p: os.path.basename(p)).tolist()
    img_paths = [os.path.join(img_folder, fname) for fname in img_files]

    autoplay = st.checkbox("▶️ Auto-play route slideshow", value=False)
    speed = st.slider("⏱️ Slide speed (seconds)", 1, 10, 3)

    if autoplay:
        img_slot = st.empty()
        for i, path in enumerate(img_paths):
            try:
                image = Image.open(path)
                img_slot.image(image, caption=f"Image {i+1}/{len(img_paths)}", use_column_width=True)
                sleep(speed)
            except:
                st.warning(f"⚠️ Could not load: {path}")
    else:
        idx = st.slider("Slide through images", 0, len(img_paths) - 1, 0)
        try:
            image = Image.open(img_paths[idx])
            st.image(image, caption=f"Image {idx+1}/{len(img_paths)}", use_column_width=True)
        except:
            st.error(f"Could not load image: {img_paths[idx]}")
