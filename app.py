import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
from geopy.distance import geodesic
from PIL import Image
from time import sleep

# === Streamlit setup ===
st.set_page_config(page_title="KAU Smart Navigator", layout="wide")

# === Paths ===
csv_folder = "AttributeTable"
img_folder = "Images/images"

# === Load Data ===
buildings = pd.read_csv(os.path.join(csv_folder, "Building_Points.csv"))
routes = pd.read_csv(os.path.join(csv_folder, "All_Solved_Routes_With_Coords.csv"))
images = pd.read_csv(os.path.join(csv_folder, "Mapillary_Images.csv"))

# === Column Mappings ===
name_field = "BuildingAr"
id_field = "ORIG_FID"
lat_field = "Shape_Y"
lon_field = "Shape_X"

# === Simulated GPS ===
user_lat = 21.4932
user_lon = 39.2465

# === App Title ===
st.title("📍 KAU Smart Navigator")

# === Show Location Toggle ===
show_location = st.checkbox("📍 Show My Location")

# === Building Selection ===
st.subheader("🧭 Choose Start and Destination")
col1, col2 = st.columns(2)
with col1:
    start = st.selectbox("Start Building", buildings[name_field])
with col2:
    end = st.selectbox("Destination Building", buildings[name_field])

# === Search Bar ===
st.markdown("### 🔍 Search for a Building")
search_query = st.text_input("Type building name...")
if search_query:
    matches = buildings[buildings[name_field].str.contains(search_query, case=False)]
    if not matches.empty:
        st.success(f"✅ Found {len(matches)} result(s):")
        for _, row in matches.iterrows():
            st.markdown(f"- **{row[name_field]}**")
            st.map(pd.DataFrame({'lat': [row[lat_field]], 'lon': [row[lon_field]]}))
    else:
        st.warning("⚠️ No matching buildings found.")

# === Map Setup ===
map_center = [user_lat, user_lon] if show_location else [21.4926, 39.2468]
m = folium.Map(location=map_center, zoom_start=16)

# === Show User Location ===
if show_location:
    folium.CircleMarker(
        location=[user_lat, user_lon],
        radius=10,
        color="green",
        fill=True,
        fill_opacity=0.9,
        popup="📍 You Are Here"
    ).add_to(m)

# === Plot Buildings ===
for _, row in buildings.iterrows():
    folium.Marker(
        location=[row[lat_field], row[lon_field]],
        popup=row[name_field],
        icon=folium.Icon(color="blue", icon="university", prefix="fa")
    ).add_to(m)

# === Try to Match Route ===
from_row = buildings[buildings[name_field] == start].iloc[0]
to_row = buildings[buildings[name_field] == end].iloc[0]
from_id = from_row[id_field]
to_id = to_row[id_field]

route_row = routes[
    ((routes["FromID"] == from_id) & (routes["ToID"] == to_id)) |
    ((routes["FromID"] == to_id) & (routes["ToID"] == from_id))
]

image_matches = pd.DataFrame()

if not route_row.empty:
    coords = [
        [from_row[lat_field], from_row[lon_field]],
        [to_row[lat_field], to_row[lon_field]]
    ]
    folium.PolyLine(
        locations=coords,
        color="red",
        weight=5,
        tooltip=f"Distance: {route_row['Length'].values[0]:.1f} m, Time: {route_row['TravelTime'].values[0]:.1f} min"
    ).add_to(m)
    st.success("✅ Route displayed!")

    # === Nearby Image Filtering ===
    def is_nearby(lat, lon, threshold=0.05):
        pt = (lat, lon)
        return (
            geodesic(pt, coords[0]).meters < threshold * 1000 or
            geodesic(pt, coords[1]).meters < threshold * 1000
        )

    image_matches = images[images.apply(lambda row: is_nearby(row["lat"], row["lon"]), axis=1)]
    image_matches = image_matches.sort_values(by="id")

else:
    st.warning("⚠️ No route match — drawing ALL available routes.")
    for _, r in routes.iterrows():
        if pd.notnull(r["From_Y"]) and pd.notnull(r["To_Y"]) and pd.notnull(r["From_X"]) and pd.notnull(r["To_X"]):
            folium.PolyLine(
                locations=[[r["From_Y"], r["From_X"]], [r["To_Y"], r["To_X"]]],
                color="orange",
                weight=2
            ).add_to(m)

# === Display Map ===
st.markdown("### 🗺️ Campus Map")
st_data = st_folium(m, width=1200, height=500)

# === Image Viewer ===
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
        idx = st.slider("Slide through images", 0, len(img_paths)-1, 0)
        try:
            image = Image.open(img_paths[idx])
            st.image(image, caption=f"Image {idx+1}/{len(img_paths)}", use_column_width=True)
        except:
            st.error(f"Could not load image: {img_paths[idx]}")
