# Read in cancer slope factors
cancslpf = pd.read_csv(cancslpf_path)

# Exposure constants for DPM to cancer risk and chronic hazard index
IFINH = 677

# CRS for shapefile output (NAD83 UTM Zone 10N)
CRS = 26910