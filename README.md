# AB617-permitted-sources
## About
This repository contains scripts to generate AERMOD input files and process AERMOD outputs for calculating and visualizing permitted source impacts. Each community is organized into its own folder, which contains two steps:
- `0-preprocess`: creates AERMOD input files to be run on the Linux cluster
- `1-postprocess`: processes AERMOD outputs to calculate and visualize cancer risk and PM2.5 concentrations
## Inputs (Dynamic)
This section lists inputs that must be updated for each new community.
- `Setup_PermittedSources_XXXX.xlsx`: Excel setup workbook for permitted sources containing the following tabs, used in both `0-preprocess` and `1-postprocess`.
  - `FacilityInfo`: facility ID, name, and coordinates of all facilities with permitted sources
  - `Release Parameters`: release parameters and coordinates for all permitted sources
  - `TAC Emissions`: TAC emissions (units of `lb/yr`) for all permitted sources
  - `PM Emissions`: PM2.5 emissions (units of `tons/yr`) for all permitted sources
  - `GDF Release`: number of gasoline and diesel nozzles and coordinates for all gasoline dispensing facilities
  - `GDF Emissions`: TAC emissions (units of `lb/yr`) for all gasoline dispensing facilities
- `modeling_grid/XXXX.shp`: shapefile for gridded modeling domain, used to assign correct cell for WRF met data assignment. Only used in `0-preprocess`.
- AERMOD output files: copy and paste outputs from Linux cluster after running. Only used in `1-postprocess`.
## Inputs (Static)
This seciton lists inputs that do not need to be updated.
- `aermod_met/*` and `met/*`: files used to compile `ME` section for AERMOD input files.
- `aermod_shell.txt`: template used to fill in AERMOD input files.
- `cancslpf.csv`: cancer slope factors for each TAC, used to calculate cancer risks.
## Outputs
- `0-preprocess`
  - `aermod/*`: AERMOD input files for each permitted source. Copy to Linux cluster to run.
- `1-postprocess`
  - `shp/permitted_pm25_cancrsk_all.shp`: shapefile with PM2.5 concentration and cancer risk at each receptor (point geometries).
  - `html/*`: HTML maps showing PM2.5 and cancer risk aggregated for all permitted sources and for the facilities with PM2.5 and toxicity-weighted emissions in the top 10 in the community modeling domain.
## How to Run
The intended workflow is:
1. Prepare input files (modeling domain shapefile and release parameters/emissions for setup workbook) and save in `0-preprocess/Input`
2. Run `run.py` from `0-preprocess` to generate AERMOD input files in `Output/aermod`
3. Copy AERMOD input files over to Linux cluster and run AERMOD
4. Copy AERMOD output files from Linux cluster to `1-postprocess/Input/aermod`
5. Run `run.py` from `1-postprocess` to generate shapefile and HTML maps for permitted source impacts
