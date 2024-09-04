import pandas as pd
import numpy as np
import geopandas as gpd
import sys
import os
import glob
from shapely.geometry import Point
import requests
import urllib

# Working directory on cluster where AERMOD files are saved
wdir = "/wrk2/ceqa/bvhp/aermod/"
# Directory on cluster where AERMOD-ready WRF met files are saved
met_cluster = "/wrk2/bkoo/mmif/mmifv342/out.wrfv41_2018_1km_aermod_yearly/"
# Path to receptors file on cluster
recs_path = "/wrk2/ceqa/bvhp/aermod/+recs/bvhp_recs_10x8.rec"

# Path to permitted sources setup file
ps_path = "Input/Setup_PermittedSources_BVHP.xlsx"

# Path to gridded modeling domain shapefile
grid_path = "Input/modeling_grid/BVHP_grid_1km_10x8.shp"

# Path to met info files
met_path = "Input/met"

# Path to AERMOD input file template
aer_inp_path = "Input/aermod_shell.txt"
with open(aer_inp_path, 'r') as inp:
    inp_shell = inp.read()


