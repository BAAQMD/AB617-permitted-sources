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

def read_plt(plt_path):
    '''
    Reads in AERMOD plotfile to DataFrame.

    Parameters
    ----------
    plt_path : str, path to plotfile.

    Returns
    -------
    plt_df : DataFrame of plotfile.

    '''
    plt_df = pd.read_csv(plt_path, sep='\s+', skiprows=7)
    plt_df = plt_df.copy().iloc[:, :10]
    plt_df.columns = ['X','Y','CONC','ZELEV','ZHILL','ZFLAG','AVE','GRP','HRS','ID']
    
    return plt_df

def calc_ems_gs(pm_emis, tac_emis, gdf_emis, cancslpf, ifinh=677):
    '''
    Reads in PM2.5 and TAC emissions by source and outputs in g/s or AERMOD processing.

    Parameters
    ----------
    pm_emis : DataFrame, PM2.5 emissions from permitted source setup file.
    tac_emis : DataFrame, TAC emissions from permitted source setup file.
    gdf_emis : DataFrame, GDF emissions from permitted source setup file.
    cancslpf : DataFrame, OEHHA cancer slope factors by TAC.
    ifinh : int, inhalation intake factor. Default value is 677.

    Returns
    -------
    pm_emis_gs : DataFrame, PM2.5 emissions by source in g/s.
    tac_emis_gs : DataFrame, TAC emissions (toxicity weighted) by source in g/s.

    '''
    # Convert PM2.5 emissions from tons/year to g/s
    pm_emis['PM25_Ems_gs'] = pm_emis['Emissions']*907184.74/365/24/3600
    pm_emis_gs = pm_emis.copy()[['DevID','PM25_Ems_gs']]
    pm_emis_gs['PM25_Ems_gs'] = pm_emis_gs['PM25_Ems_gs'].fillna(0)
    
    # Concatenate tac_emis and gdf_emis
    tac_emis_all = pd.concat([tac_emis, gdf_emis])
    # Convert PM2.5 emissions from lb/year to g/s
    tac_emis_all['Ems_gs'] = tac_emis_all['Emissions']*453.592/365/24/3600
    # Calculate toxicity-weighted emissions from TACs
    tac_emis_all.rename(columns={'Pollutant#':'POL'}, inplace=True)
    tac_emis_all = tac_emis_all.merge(cancslpf, how='left', on='POL')
    tac_emis_all = tac_emis_all.fillna(0)
    tac_emis_all['TWE_Ems_gs'] = tac_emis_all['Ems_gs']*ifinh*tac_emis_all['CANCSLPFC']
    tac_emis_gs = tac_emis_all.groupby(['DevID']).sum()[['TWE_Ems_gs']].reset_index()
    
    return pm_emis_gs, tac_emis_gs

def calc_conc_total(pm_emis_gs, tac_emis_gs, dev_list, aermod_path='Input/aermod'):
    '''
    Calculates total PM2.5 concentrations and cancer risks from all permitted sources.

    Parameters
    ----------
    pm_emis_gs : DataFrame, PM2.5 emissions by source in g/s.
    tac_emis_gs : DataFrame, TAC emissions (toxicity weighted) by source in g/s.
    dev_list : list of devices/sources to include in calculating total impacts.

    Returns
    -------
    conc_gdf : GeoDataFrame, PM2.5 concentration and cancer risk by receptor.

    '''
    # Read in plotfiles for all sources to calculate concentrations
    # Preallocate DataFrames for PM2.5 concentration and cancer risk
    conc_all = pd.DataFrame(columns=['X','Y','PM2.5_CONC', 'CANCRSK'])
    for dev in dev_list:
        try:
            plt_df = read_plt("{}/{}/PE_{}.PLT".format(aermod_path, dev, dev))
            plt_df['DevID'] = dev            
            # Merge plt_df on emissions DataFrames
            conc = plt_df[['X','Y','CONC','DevID']].merge(pm_emis_gs, on='DevID', how='left')
            conc = conc.merge(tac_emis_gs, on='DevID', how='left')
            # Calculate PM2.5 concentration and cancer risk
            try:
                conc['PM2.5_CONC'] = conc['PM25_Ems_gs']*conc['CONC']
            except KeyError:
                conc['PM2.5_CONC'] = 0
            try:
                conc['CANCRSK'] = conc['TWE_Ems_gs']*conc['CONC']
            except KeyError:
                conc['CANCRSK'] = 0
            conc = conc.copy()[['X','Y','PM2.5_CONC', 'CANCRSK']]
            conc_all = pd.concat([conc_all, conc])
            conc_all = conc_all.groupby(['X','Y']).sum().reset_index()
            print(dev)
        except FileNotFoundError:
            pass
    conc_gdf = create_pts(conc_all)
    conc_gdf['PM2.5_CONC'] = np.round(conc_gdf['PM2.5_CONC'], 2)
    conc_gdf['CANCRSK'] = np.round(conc_gdf['CANCRSK'], 2)
    conc_gdf.to_file('Output/shp/permitted_pm25_cancrsk_all.shp')
    
    return conc_gdf

def plot_map(conc_gdf, out_path, plot_col = None, label = None, tooltip = True, vmax = None, thres = 0):
    '''
    Saves an interactive map of concentrations to .html file. 

    Parameters
    ----------
    conc_gdf : GeoDataFrame, with X/Y points as geometries and concentrations
               as data columns.
    out_path : str, path to save file to.
    plot_col : str, column in conc_gdf to use for color scale.
    label : str, label to use for plotting.
    tooltip : bool or list, if list is passed, map will display info from 
              selected columns in list on hover. True displays all columns,
              False displays nothing.
    vmax : float, maximum value to establish for color scale. Default is None,
           which will select the value automatically.
    thres : float, minimum threshold value for displaying data on maps.

    Returns
    -------
    None, saves map to disk.

    '''
    conc_gdf = conc_gdf.copy().loc[conc_gdf[plot_col] > thres]
    if plot_col is None:
        m = conc_gdf.explore(tiles='CartoDB positron',
                             tooltip=tooltip,
                             marker_type='circle',
                             marker_kwds={'radius':25,
                                          'fill':True},
                             style_kwds={'stroke':False})
    else:
        conc_gdf.rename(columns={plot_col:label}, inplace=True)
        m = conc_gdf.explore(tiles='CartoDB positron',
                             column=label,
                             tooltip=tooltip,
                             vmax=vmax,
                             marker_type='circle',
                             marker_kwds={'radius':25,
                                          'fill':True},
                             style_kwds={'stroke':False})
    m.save(out_path)  


