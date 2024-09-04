def read_setup_file(ps_path):
    '''
    Reads in permitted source setup file and parses into multiple DataFrames.

    Parameters
    ----------
    ps_path : str, path to permitted source setup file.

    Returns
    -------
    None.

    '''
    ps_setup = pd.read_excel(ps_path, sheet_name=None)
    fac_info = ps_setup['Facility Info']
    rel_params = ps_setup['Release Parameters']
    pm_emis = ps_setup['PM Emissions']
    tac_emis = ps_setup['TAC Emissions']
    gdf_rel = ps_setup['GDF Release']
    gdf_emis = ps_setup['GDF Emissions']
    
    return fac_info, rel_params, pm_emis, tac_emis, gdf_rel, gdf_emis

def get_elev(df, lat_col, lon_col):
    '''
    Retrieves elevations from USGS API given lat/lon coordinates. 
    
    Parameters
    ----------
    df : DataFrame, contains lat and lon columns.
    lat_col : str, column containing lat values.
    lon_col : str, column containing lon values.

    Returns
    -------
    df : DataFrame, retains same data with added column for elevation.

    '''
    url = r'https://epqs.nationalmap.gov/v1/json?'
    elevations = []
    for lat, lon in zip(df[lat_col], df[lon_col]):
                
        # define rest query params
        params = {
            'output': 'json',
            'x': lon,
            'y': lat,
            'units': 'Meters'
        }
        
        # format query string and return query value
        result = requests.get((url + urllib.parse.urlencode(params)))
        elevations.append(result.json()['value'])

    df['elev_m'] = elevations
    df['elev_m'] = df['elev_m'].apply(lambda x:float(x))
    
    return df

def create_pts(conc, x_col = 'X', y_col = 'Y', crs = 26910):
    '''
    Creates point geometries and converts concentration DataFrame to GeoDataFrame.

    Parameters
    ----------
    conc : DataFrame, contains columns for X/Y coordinates and concentration or other metric.
    x_col : str, column name for X coordinate. The default is 'X'.
    y_col : str, column name for Y coordinate. The default is 'Y'.
    crs : int, coordinate reference system for point geometries. Should match CRS of input data.
               For example, lat/lon should use crs=4326. The default is 26910 and CRS is converted
               to 26910 as the final step to meet AERMOD requirements.

    Returns
    -------
    conc_gdf : GeoDataFrame, contains same information as conc but with point geometries.

    '''
    pts = [Point(xy) for xy in zip(conc[x_col], conc[y_col])]
    conc_gdf = gpd.GeoDataFrame(conc, geometry = pts, crs = crs)
    conc_gdf = conc_gdf.to_crs(26910)
    
    return conc_gdf

def assign_src_type(src_df):
    '''
    Assigns point source type (POINT, POINTCAP, POINTHOR) based on columns in src_df.

    Parameters
    ----------
    src_df : DataFrame, contains point source release parameters.

    Returns
    -------
    src_df : DataFrame, with added column for source type.

    '''
    src_df['Source Type'] = src_df['Source Type'].apply(lambda x:'POINT' if x=='STACK' else x)
    src_df['Source Type'] = src_df['Source Type'].apply(lambda x:'POINT' if x=='BUG' else x)
    src_df['Source Type'] = src_df.apply(lambda x:'POINTCAP' if not pd.isnull(x['Rain Cap']) else x['Source Type'], axis=1)
    src_df['Source Type'] = src_df.apply(lambda x:'POINTHOR' if x['Outlet']=='H' else x['Source Type'], axis=1)
    
    return src_df

def format_grid(grid, I_offset, J_offset, crs=26910):
    '''
    Creates and extracts column I_J based on converted grid cell coordinates from CARB to BAAQMD.

    Parameters
    ----------
    grid : GeoDataFrame, contains polygon geometries of grid cells.
    I_offset : int, offset (x-direction) required to convert CARB grid cell ID to BAAQMD.
    J_offset : int, offset (y-direction) required to convert CARB grid cell ID to BAAQMD.

    Returns
    -------
    None.

    '''
    grid['I_CELL'] = grid['I_CELL'] + I_offset
    grid['J_CELL'] = grid['J_CELL'] + J_offset
    grid['I_J'] = grid.apply(lambda x:"{}_{}".format(int(x.I_CELL), int(x.J_CELL)), axis=1)
    grid = grid.copy()[['I_J','geometry']]
    grid = grid.to_crs(crs)
    
    return grid

def join_grid(src_gdf, grid):
    '''
    Performs spatial join between point geometries and grid to assign grid cell coordinates to each source.

    Parameters
    ----------
    src_gdf : GeoDataFrame, contains point geometries of source locations.
    grid : GeoDataFrame, contains polygon geometries of grid cells.

    Returns
    -------
    src_gdf : GeoDataFrame, src_gdf with added column "I_J" for grid cell coordinates.

    '''
    src_gdf = src_gdf.sjoin(grid)
    src_gdf.drop(columns='index_right', inplace=True)
    
    return src_gdf

def write_point_src(src_id, src_type, x1, y1, z1, hgt, diam, temp, vel, out_dir):
    '''
    Parameters
    ----------
    src_id : str, ID to assign area source
    src_type : str, one of POINT, POINTHOR, POINTCAP to designate type of point source
    x1 : float, x coordinate of point source
    y1 : float, y coordinate of point source
    z1 : float, elevation of point source in meters
    hgt : float, stack height in meters
    diam : float, stack diameter in meters
    temp : float, stack temperature in K
    vel : float, stack velocity in m/s
    out_dir : str, directory to write .src file to

    Returns
    -------
    None, saves .src file to out_dir.

    '''
    loc_str = '{} LOCATION {:>10} {} {:11.4f} {:11.4f} {:7.2f}\n'
    param_str = '{} SRCPARAM {:>10} {:5.3f} {:5.3f} {:7.3f} {:5.3f} {:5.3f}\n'
    
    so_loc = loc_str.format('  ', src_id, src_type, x1, y1, z1)
    so_param = param_str.format('  ', src_id, 1, hgt, temp, vel, diam)
    
    so_src = so_loc + so_param
    so_src += '   URBANSRC ALL\n'
    so_src += '   SRCGROUP ALL\n'
    convert_unix(so_src, out_dir+"/{}.src".format(src_id))

def write_volume_src(src_id, x1, y1, z1, relhgt, syinit, szinit, out_dir):
    '''
    Parameters
    ----------
    src_id : str, ID to assign volume source
    x1 : float, x coordinate of volume source
    y1 : float, y coordinate of volume source
    z1 : float, elevation of volume source in meters
    relhgt : float, release height in meters
    syinit : float, initial lateral dimension in meters
    szinit : float, initial vertical dimension in meters
    out_dir : str, directory to write .src file to

    Returns
    -------
    None, saves .src file to out_dir.

    '''
    loc_str = '{} LOCATION {:>10} VOLUME {:11.4f} {:11.4f} {:7.2f}\n'
    param_str = '{} SRCPARAM {:>10} {:5.3f} {:5.3f} {:5.3f} {:5.3f}\n'
    
    so_loc = loc_str.format('  ', src_id, x1, y1, z1)
    so_param = param_str.format('  ', src_id, 1, relhgt, syinit, szinit)
    
    so_src = so_loc + so_param
    so_src += '   URBANSRC ALL\n'
    so_src += '   SRCGROUP ALL\n'
    so_path = out_dir
    convert_unix(so_src, so_path+"/{}.src".format(src_id))
    
def write_met(met_path, met_cluster, ij):
    '''
    Writes and returns met (ME) portion of AERMOD input file.

    Parameters
    ----------
    met_path : str, local path to where met info files are saved.
    met_cluster : str, path on cluster to AERMOD .sfc files.
    ij : str, I_J coordinates of met data to extract.

    Returns
    -------
    met : str, met (ME) portion of AERMOD input file to be written.

    '''
    met_file = '{}/CELLIJ_{}.info.txt'.format(met_path, ij)
    with open(met_file, 'r') as f:
        met = f.read()
    met = met.replace('CELLIJ', met_cluster+'CELLIJ')
    
    return met

def write_ou(src_id):
    '''
    Writes and returns output (OU) portion of AERMOD input file.

    Parameters
    ----------
    src_id : str, source ID of modeled source.

    Returns
    -------
    ou : str, output (OU) portion of AERMOD input file to be written.

    '''
    ou = ''
    ou += '   PLOTFILE 1 ALL 1ST H1G_{}.PLT\n'.format(src_id)
    ou += '   PLOTFILE PERIOD ALL PE_{}.PLT'.format(src_id)
    
    return ou

def convert_unix(s, path):
    '''    
    Converts text file from DOS to Unix line endings.
    
    Parameters
    ----------
    s : str, to write to disk and convert to Unix line endings.
    path : str, path to write text file to.

    '''
    with open(path, 'w') as f:
        f.write(s)
    with open(path, 'rb') as f_in:
        t = f_in.read()
    t = t.replace(b'\r\n', b'\n')
    with open(path, 'wb') as f_out:
        f_out.write(t)
        
def create_inp(inp_shell, so, re, me, ou, out_path):
    '''
    Writes AERMOD input file for a single source to disk.
    
    Parameters
    ----------
    inp_shell : str, path to input file format to fill in.
    SO: str, to fill {} in source pathway
    RE: str, to fill {} in receptor pathway
    ME: str, to fill {} in meteorology pathway
    OU: str, to fill {} in output pathway
    out_path : str, path to save .inp file to.

    Returns
    -------
    inp : str, to be written to .inp file

    '''
    # Construct and save input file
    inp = inp_shell.format(so, re, me, ou)
    convert_unix(inp, out_path)
    
    return inp

def write_aermod_permitted(src_df):
    '''
    Writes and saves aermod input files for each permitted source.

    Parameters
    ----------
    src_df : GeoDataFrame, contains release parameters and point geometries for all sources.

    Returns
    -------
    None, writes AERMOD input files to Output folder.

    '''
    src_list = src_df.DevID.tolist()
    if not os.path.exists('Output/aermod'):
        os.makedirs('Output/aermod')
    for srcid in src_list:
        out_path = 'Output/aermod/{}'.format(srcid)
        if not os.path.exists(out_path):
            os.makedirs(out_path)
        src_gdf = src_df.copy().loc[src_df.DevID == srcid]
        # Create src file
        srctype = src_gdf['Source Type'].values[0]
        x1 = src_gdf.geometry.x.values[0]
        y1 = src_gdf.geometry.y.values[0]
        z1 = src_gdf.elev_m.values[0]
        if srctype == "VOLUME":
            relhgt = src_gdf.Relhgt_m.values[0]
            syinit = src_gdf.Syinit_m.values[0]
            szinit = src_gdf.Szinit_m.values[0]
            write_volume_src(srcid, x1, y1, z1, relhgt, syinit, szinit, out_path)
        else:
            hgt = src_gdf.Stkht_m.values[0]
            diam = src_gdf.Stkdiam_m.values[0]
            temp = src_gdf.Temp_K.values[0]
            vel = src_gdf.Vel_ms.values[0]
        write_point_src(srcid, srctype, x1, y1, z1, hgt, diam, temp, vel, out_path)
        # Write SO section
        so = "{}.src".format(srcid)
        # Write RE section
        re = recs_path
        # Write ME section
        ij = src_gdf.I_J.values[0]
        met = write_met(met_path, met_cluster, ij)
        # Write OU section
        ou = write_ou(srcid)
        # Output path for AERMOD input file
        out_aer_path = 'Output/aermod/{}/aermod.inp'.format(srcid)
        # Write and save AERMOD input file
        create_inp(inp_shell, so, re, met, ou, out_aer_path)
        
def write_aermod_gdf(src_df):
    '''
    Writes and saves aermod input files for each GDF.

    Parameters
    ----------
    src_df : GeoDataFrame, contains nozzle count and point geometries for all GDFs.

    Returns
    -------
    None, writes AERMOD input files to Output folder.

    '''
    src_list = src_df.DevID.tolist()
    src_df['# gas nozzles'] = src_df['# gas nozzles'].fillna(0)
    src_df['# diesel nozzles'] = src_df['# diesel nozzles'].fillna(0)
    if not os.path.exists('Output/aermod'):
        os.makedirs('Output/aermod')
    for srcid in src_list:
        out_path = 'Output/aermod/{}'.format(srcid)
        if not os.path.exists(out_path):
            os.makedirs(out_path)
        src_gdf = src_df.copy().loc[src_df.DevID == srcid]
        # Create src file
        srctype = src_gdf['Source Type'].values[0]
        x1 = src_gdf.geometry.x.values[0]
        y1 = src_gdf.geometry.y.values[0]
        z1 = src_gdf.elev_m.values[0]
        relhgt = 1.03
        n = src_gdf['# gas nozzles'].values[0] + src_gdf['# diesel nozzles'].values[0]
        syinit = -0.00393*n**2 + 0.3292*n + 0.7285
        szinit = 1.03/2.15
        write_volume_src(srcid, x1, y1, z1, relhgt, syinit, szinit, out_path)
        # Write SO section
        so = "{}.src".format(srcid)
        # Write RE section
        re = recs_path
        # Write ME section
        ij = src_gdf.I_J.values[0]
        met = write_met(met_path, met_cluster, ij)
        # Write OU section
        ou = write_ou(srcid)
        # Output path for AERMOD input file
        out_aer_path = 'Output/aermod/{}/aermod.inp'.format(srcid)
        # Write and save AERMOD input file
        create_inp(inp_shell, so, re, met, ou, out_aer_path)
        