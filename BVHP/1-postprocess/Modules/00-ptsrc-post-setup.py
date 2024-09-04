import pandas as pd
import numpy as np
import geopandas as gpd
import glob
from shapely.geometry import Point

# Path to AERMOD outputs
aermod_path = "Input/aermod"

# Path to permitted sources setup file
ps_path = "Input/Setup_PermittedSources_BVHP.xlsx"

# Path to cancer slope factors
cancslpf_path = "Input/cancslpf.csv"
