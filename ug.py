import streamlit as st
import ee
import geemap
from datetime import datetime

# Authenticate with Earth Engine
ee.Authenticate()
ee.Initialize(project="ee-tusharshingane232")

# Streamlit Title and Instructions
st.title("Flood Hazard Mapping using Sentinel-1 SAR Data")
st.write("This app shows the analysis of flood hazard mapping for the region of Assam based on Sentinel-1 SAR data.")

# User input: Location and Date ranges
location = st.selectbox("Select Location", ["Assam", "Other Location"])  # Example for selection

goodDate = st.date_input("Good Date", datetime(2024, 4, 1))
floodDate = st.date_input("Flood Date", datetime(2024, 5, 29))

floodStart = st.date_input("Flood Start", datetime(2024, 6, 15))
floodEnd = st.date_input("Flood End", datetime(2024, 7, 21))

# Load provincial boundaries and other datasets
Province = ee.FeatureCollection("projects/ee-tusharshingane232/assets/Provincial_Boundary")
Indian_Province = ee.FeatureCollection("projects/ee-tusharshingane232/assets/geoBoundaries-IND-ADM2_simplified")
state = ee.FeatureCollection("projects/ee-tusharshingane232/assets/geoBoundaries-IND-ADM1")

# Filter the state based on user input
states = ee.FeatureCollection(state)
sindh = states.filterMetadata("shapeName", "equals", location)

# Map initialization using Geemap
Map = geemap.Map()

# Add boundary layer to map
Map.addLayer(sindh, {}, "Affected Region Boundary")
Map.centerObject(sindh)

# Fetch Sentinel-1 SAR Data
Sentinel_Sar = ee.ImageCollection("COPERNICUS/S1_GRD")

filtered_collection = Sentinel_Sar.filterBounds(sindh).filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')).filter(ee.Filter.eq('instrumentMode', 'IW')) \
    .filter(ee.Filter.Or(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'), ee.Filter.eq('orbitProperties_pass', 'ASCENDING')))

# Filter the data for good and flood periods
goodState = filtered_collection.filterDate(str(goodDate), str(floodDate))
floodState = filtered_collection.filterDate(str(floodStart), str(floodEnd))

# Process Sentinel-1 Data (functions from your original code)
goodImage = goodState.select("VH").mosaic().clip(sindh)
floodImage = floodState.select("VH").mosaic().clip(sindh)

def toNatural(img):
    return ee.Image(10.0).pow(img.select(0).divide(10.0))

def toDB(img):
    return ee.Image(img).log10().multiply(10.0)

def RefinedLee(img):
    weights3 = ee.List.repeat(ee.List.repeat(1, 3), 3)
    kernel3 = ee.Kernel.fixed(3, 3, weights3, 1, 1, False)
    mean3 = img.reduceNeighborhood(ee.Reducer.mean(), kernel3)
    variance3 = img.reduceNeighborhood(ee.Reducer.variance(), kernel3)
    # Add other logic based on the function you already have...

goodFilter = toDB(RefinedLee(toNatural(goodImage)))
floodFilter = toDB(RefinedLee(toNatural(floodImage)))

# Adding layers to the map
Map.addLayer(goodFilter, {"min": -25, "max": 0}, "Good Filter")
Map.addLayer(floodFilter, {"min": -25, "max": 0}, "Flood Filter")

# Compute flood mask and water body mask
flood = goodFilter.gt(-20).And(floodFilter.lt(-20))
floodMask = flood.updateMask(flood.eq(1))

water = goodFilter.lt(-20).And(floodFilter.lt(-20))
waterMask = water.updateMask(water.eq(1))

# Visualization Parameters
Map.addLayer(floodMask, {'visParams': {'palette': ['Red']}}, "Flood Water")
Map.addLayer(waterMask, {'visParams': {'palette': ['yellow']}}, "Water Body")

# Distance from Flood layer
distanceFromFlood = floodMask.fastDistanceTransform(2).clip(sindh)
heatmapPalette1 = ['red', 'orange', 'yellow', 'lightgreen', 'green']
Map.addLayer(distanceFromFlood, {"min": 0, "max": 5000, "palette": heatmapPalette1}, "Distance from Flood")

# Elevation and hazard layers (SRTM)
elevation = ee.Image("USGS/SRTMGL1_003").clip(sindh)
Map.addLayer(elevation, {"min": 0, "max": 100, "palette": ['green', 'yellow', 'red', 'white']}, 'DEM', False)

# Run hazard score calculations and add to map
# Your other hazard scores will be calculated similarly and added here...
# Adding flood hazard score layer
floodHazard = floodMask.add(elevation)  # This would be an example of how to add other score layers
Map.addLayer(floodHazard, {"min": 1, "max": 15, "palette": heatmapPalette1}, 'Flood Hazard Score')

# Display the map
st.write("### Map Visualization")
Map.to_streamlit(height=600)

