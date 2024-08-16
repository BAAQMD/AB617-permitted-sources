# Read in DataFrames from Excel setup file
fac_info, rel_params, pm_emis, tac_emis, gdf_rel, gdf_emis = read_setup_file(ps_path)

# Read in and reformat grid
grid = gpd.read_file(grid_path)
grid = format_grid(grid, I_offset, J_offset)

# Process permitted source release parameters
print("Retrieving elevations for permitted sources")
rel_params = get_elev(rel_params, 'Y_USERCOORD', 'X_USERCOORD')
rel_params = create_pts(rel_params, x_col='X_USERCOORD', y_col='Y_USERCOORD', crs=4326)
rel_params = assign_src_type(rel_params)
rel_params = join_grid(rel_params, grid)

# Process GDF release parameters
print("Retrieving elevations for GDFs")
gdf_rel = get_elev(gdf_rel, 'Y_USERCOORD', 'X_USERCOORD')
gdf_rel = create_pts(gdf_rel, x_col='X_USERCOORD', y_col='Y_USERCOORD', crs=4326)
gdf_rel['Source Type'] = "VOLUME"
gdf_rel = join_grid(gdf_rel, grid)

# Write AERMOD input files
print("Writing AERMOD input files")
write_aermod_permitted(rel_params)
write_aermod_gdf(gdf_rel)

