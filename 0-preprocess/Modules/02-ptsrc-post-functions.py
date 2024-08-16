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

def read_ems(ems_path, nvol_path):
    '''
    Reads in emissions and nvolumes files and produces emissions DataFrame.

    Parameters
    ----------
    ems_path : str, path to emissions file.
    nvol_path : str, path to nvolumes file.

    Returns
    -------
    ems_df : DataFrame, PM10 and PM2.5 emissions by rail link.

    '''
    ems = pd.read_csv(ems_path)
    nvol = pd.read_csv(nvol_path)
    nvol['FID_RR'] = nvol['segmentID'].apply(lambda x:int(x.split('_')[0].replace('RAI','')))
    nvol = nvol.groupby(['FID_RR']).sum().reset_index()
    ems_df = ems.merge(nvol[['FID_RR','nvols']], on='FID_RR', how='outer')
    ems_df.fillna(0, inplace=True)
    
    # Convert emissions from g/day to g/s
    ems_df['EMS_PM10'] = ems_df['PM10_g_day']/ems_df['nvols']/24/3600
    ems_df['EMS_PM2.5'] = ems_df['PM2.5_g_day']/ems_df['nvols']/24/3600
    ems_df = ems_df[['FID_RR','EMS_PM10','EMS_PM2.5']]
    
    return ems_df

def calc_conc(plt_df, ems_df):
    '''
    Calculates PM concentrations and health risks.

    Parameters
    ----------
    plt_df : DataFrame, output from read_plt (plotfile results).
    ems_df : DataFrame, output from read_ems (emission rates).

    Returns
    -------
    conc_gdf : GeoDataFrame, containing PM2.5 concentration, cancer risk, 
               chronic HI by modeled receptor. 

    '''
    conc = plt_df[['X','Y','CONC','FID_RR']].merge(ems_df, on='FID_RR', how='left')
    conc['CONC_PM10'] = conc['EMS_PM10']*conc['CONC']
    conc['CONC_PM2.5'] = conc['EMS_PM2.5']*conc['CONC']
    conc['CANC_RISK'] = conc['CONC_PM10']*IFINH*SLOPE
    conc['CHRON_HI'] = conc['CONC_PM10']/CREL
    conc.drop(columns=['CONC','FID_RR','EMS_PM10','EMS_PM2.5'], inplace=True)
    conc_tot = conc.groupby(['X','Y']).sum().reset_index()
    pts = [Point(xy) for xy in zip(conc_tot['X'], conc_tot['Y'])]
    conc_gdf = gpd.GeoDataFrame(conc_tot, geometry=pts, crs= CRS)
    conc_gdf.drop(columns=['X','Y'], inplace=True)
    
    return conc_gdf



