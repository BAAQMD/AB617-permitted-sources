# Read in DataFrames from Excel setup file
fac_info, rel_params, pm_emis, tac_emis, gdf_rel, gdf_emis = read_setup_file(ps_path)

# Output emissions in g/s for use in AERMOD processing
pm_emis_gs, tac_emis_gs = calc_ems_gs(pm_emis, tac_emis, gdf_emis, cancslpf)

# Output GeoDataFrame and shapefile for total permitted source impacts
devs = pd.concat([pm_emis_gs.DevID, tac_emis_gs.DevID])
devs = devs.drop_duplicates().tolist()
conc_gdf = calc_conc_total(pm_emis_gs, tac_emis_gs, devs)
plot_map(conc_gdf, "Output/html/pm25_permitted_all.html", "PM2.5_CONC", "PM2.5 Concentration (\u03bcg/m3)")
plot_map(conc_gdf, "Output/html/cancrsk_permitted_all.html", "CANCRSK", "Cancer Risk (in a million)")

# Calculate PM2.5 concentration and cancer risk by source for the top 10 emitting facilities
pm25_by_fac = pm_emis_gs.copy()
pm25_by_fac['FacID'] = pm25_by_fac['DevID'].apply(lambda x:x.split('-')[0])
pm25_by_fac = pm25_by_fac.groupby(['FacID']).sum().reset_index()
pm25_top10 = pm25_by_fac.sort_values(by='PM25_Ems_gs', ascending=False).reset_index(drop=True).iloc[:10]
pm25_top10_list = pm25_top10.FacID.tolist()
for fac in pm25_top10_list:
    devs_fac = [dev for dev in devs if dev.split("-")[0]==fac]
    conc_fac_gdf = calc_conc_total(pm_emis_gs, tac_emis_gs, devs_fac)
    plot_map(conc_fac_gdf, "Output/html/pm25_{}.html".format(fac), "PM2.5_CONC", "PM2.5 Concentration (\u03bcg/m3)", thres = 0.1)

tac_by_fac = tac_emis_gs.copy()
tac_by_fac['FacID'] = tac_by_fac['DevID'].apply(lambda x:x.split('-')[0])
tac_by_fac = tac_by_fac.groupby(['FacID']).sum().reset_index()
tac_top10 = tac_by_fac.sort_values(by='TWE_Ems_gs', ascending=False).reset_index(drop=True).iloc[:10]
tac_top10_list = tac_top10.FacID.tolist()
for fac in tac_top10_list:
    devs_fac = [dev for dev in devs if dev.split("-")[0]==fac]
    conc_fac_gdf = calc_conc_total(pm_emis_gs, tac_emis_gs, devs_fac)
    plot_map(conc_fac_gdf, "Output/html/cancrsk_{}.html".format(fac), "CANCRSK", "Cancer Risk (in a million)", thres = 1)
    
fac_info['PlantNo'] = fac_info['PlantNo'].apply(lambda x:str(x))
pm25_top10 = pm25_top10.merge(fac_info[['PlantNo','Name']], left_on='FacID', right_on='PlantNo', how='left')
pm25_top10['PM25_Ems_tpy'] = np.round(pm25_top10['PM25_Ems_gs']*34.7625,2)
pm25_top10[['FacID','Name','PM25_Ems_tpy']].to_csv("Output/html/PM25_top10_facilities.csv", index=False)

tac_top10 = tac_top10.merge(fac_info[['PlantNo','Name']], left_on='FacID', right_on='PlantNo', how='left')
tac_top10['TWE_Ems_gs'] = np.round(tac_top10['TWE_Ems_gs'],3)
tac_top10[['FacID','Name','TWE_Ems_gs']].to_csv("Output/html/TAC_top10_facilities.csv", index=False)