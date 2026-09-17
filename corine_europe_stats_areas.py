# -*- coding: utf-8 -*-
"""
Created on Tue Apr 16 12:06:34 2024

Modified by Merret Buurman, IGB, February 2025

Modified by Eero Alkio, Syke, 12th February 2026 for European scale and finalized 9/2026 

"""

from rasterstats import zonal_stats
import os, glob, re
import geopandas as gpd
import pandas as pd
import logging
import rasterio
import datetime

LOGGER = logging.getLogger(__name__)

def corine_stats_real_areas(input_polygons_path, input_path_rasters, input_path_headers, output_path, string_for_output_name, contact_email=None):
    
    ## Input rasters as list of hardcoded urls
    rasters = sorted(input_path_rasters)

    # Warn if no rasters 
    if len(rasters) == 0:
        LOGGER.error('No input raster paths incdluded found in: %s' % input_path_rasters)
        if contact_email is None:
            raise ValueError('No input rasters found. Please check in input raster list: %s' % input_path_rasters)
        else:
            # If this is run on an AquaINFRA server, users cannot check the input directory, but have to contact someone:
            raise ValueError('No input rasters found. Please contact service owner (%s)' % contact_email)
        
    # Polygons and rasters must be in the same CRS -> reproject
    areas = gpd.read_file(input_polygons_path)
    
    ## Raising error if no CRS is defined. 
    if areas.crs is None:
        print(f"Missing crs for polygon {input_polygons_path}")
        raise ValueError("Missing CRS - the input polygon file must have a defined CRS")
    
    ## Getting the raster crs from the first input raster (These should all have the same CRS)
    with rasterio.open(rasters[0]) as src:
        raster_crs = src.crs  

    ## Reprojecting vector data to same crs as the first input raster
    if areas.crs != raster_crs:
        areas = areas.to_crs(raster_crs)

    ## Read land cover classes for European Harmonized CLC, extracted from 
    ## https://www.eea.europa.eu/en/datahub/datahubitem-view/a55d9224-a326-4cb1-9b9c-3a324520341a?activeAccordion=1069872%2C1069945%2C1069947%2C1069948 version 20
    in_corineheader0 = '%s/harmonized_corine_europe_headers_2018.csv' % input_path_headers

    corineheader  = pd.read_csv(in_corineheader0, sep=',')

    # Collect output paths:
    output_csvs = []

    # Iterate over catchments areas
    i = 0
    LOGGER.debug('Iterating over the areas...')
    for idx, area in areas.iterrows():
        i += 1
        ## Fall back to an auto-generated name if areaname is missing or empty EA
        has_areaname = "areaname" in areas.columns and pd.notna(area.get("areaname")) and str(area.get("areaname")).strip() != ""
        if not has_areaname:
            area["areaname"] = "area_%s" % i
            LOGGER.warning('Area %s in file %s has no areaname attribute - using fallback name "%s" instead.' % (i, input_polygons_path, area["areaname"]))

        LOGGER.debug('Area %s: %s' % (i, area.areaname))
        #LOGGER.debug(area) # show the attributes from the shapefile!
        area = area[['areaname', 'geometry']]
        arearesults = pd.DataFrame()

        # Iterate over Corine years
        j = 0
        LOGGER.debug('Now iterate over the %s rasters for area %s...' % (len(rasters), area.areaname))
        for raster in rasters:
            j += 1
            rastername = os.path.basename(raster).replace('.tif','')
            LOGGER.debug('Raster %s (for area %s): %s' % (j, area.areaname, rastername))
            raster_year = rastername[3:7]
            ## Storing the year and name of the raster to results
            area_data = area.copy()
            area_data['Year'] = raster_year
            area_data['Raster'] = rastername

            # Extract land use pixel counts per classes
            zs = zonal_stats([area_data.geometry], raster=raster, categorical=True)
            
            ## In European CLC rasters pixel size is 100m x 100m -> ha, no need for conversions
            stats_hectare = pd.DataFrame(zs).fillna(0)

            ## converting raw raster values to corine level 1 classes EA
            ## Here it is also possible to convert Corine level 2 or 3 with "LABEL2" or "LABEL3"

            mapping = corineheader.set_index('Value')['LABEL1'].to_dict()
            stats_hectare = stats_hectare.rename(columns=mapping)

            ## Combining all level 1 classes into total area of the class EA
            stats_hectare2 =stats_hectare.T.groupby(level=0, sort=False).sum().T
            
            ## Adding the results to dataframe EA
            results = pd.concat([area_data, stats_hectare2.iloc[0]], axis=0)
            
            df = pd.DataFrame(results.drop('geometry'))
            
            # Combine different years
            arearesults = pd.concat([arearesults, df], axis=1)

        ## Adjusting results to clearer format
        arearesults = arearesults.T.set_index('Year')

        LOGGER.debug('Done iterating over rasters for this area... (%s)' % area.areaname)
        #LOGGER.debug(arearesults) # This is long!

        # Make ASCII, filename-safe name: drop non-ASCII chars, replace the rest of unsafe chars with underscores
        areaname_ascii = ''.join(c for c in area.areaname if 0 < ord(c) < 127)
        areaname_ascii = re.sub(r'[^A-Za-z0-9._-]+', '_', areaname_ascii).strip('_')
        if not areaname_ascii:
            areaname_ascii = 'area_%s' % i
        LOGGER.debug('Area name in ASCII: BEFORE: %s, AFTER: %s' % (area.areaname, areaname_ascii))

        filename = 'europe_corine_stats_real_areas_%s_%s.csv' % (areaname_ascii, string_for_output_name)

        filepath = '%s/%s' % (output_path, filename)

        # Store to CSV:
        LOGGER.debug('Storing to: %s' % filepath)

        arearesults.to_csv(filepath, sep=';', float_format="%.2f")

        # Create result dict:
        output_csvs.append({
           "area_name": areaname_ascii,
           "area_name_specialchars": area.areaname,
           "file_name": filename,
           "file_path": filepath
        })


    return arearesults, output_csvs

'''
To run this code locally, define the paths for inputs and outputs here.

The outputs will be one csv file per area, named as follows:
europe_corine_stats_real_areas_<areaname>_<string_for_output_name>.csv

For example:
europe_corine_stats_real_areas_Finland.csv
europe_corine_stats_real_areas_Sweden.csv
europe_corine_stats_real_areas_Norway.csv

'''

if __name__ == "__main__":

    # Tell python to log to console, at debug level:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)5s - %(message)s')
    # Alternatively, to file:
    #logging.basicConfig(level=logging.DEBUG, filename='corine_stats_real_areas.log', format='%(asctime)s - %(name)s - %(levelname)5s - %(message)s')

    ## DON'T CHANGE THE INPUT HEADERS - THEY ARE FIXED FOR HARMONIZED CORINE-DATASETS
    input_path_headers = "./example_inputs/"

    ## INSERT THE INPUT POLYGON WITH "areaname"-ATTRIBUTE HERE
    input_polygons_path = "./example_inputs/corine_tool_input.gpkg"

    ## Hardcoded harmonized input CORINE rasters for Europe, 100m reoslution
    input_path_rasters = [
        "https://aquainfra-syke.a3s.fi/europe_clc_cog_raster/CLC2000ACC_V2018_20_cog.tif",
        "https://aquainfra-syke.a3s.fi/europe_clc_cog_raster/CLC2006ACC_V2018_20_cog.tif",
        "https://aquainfra-syke.a3s.fi/europe_clc_cog_raster/CLC2012ACC_V2018_20_cog.tif",
        "https://aquainfra-syke.a3s.fi/europe_clc_cog_raster/CLC2018ACC_V2018_20_cog.tif"
    ]
    ## Modify the output path if needed
    output_path = "./example_outputs"
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    string_for_output_name = datetime.datetime.today().strftime('%Y-%m-%d')  # will be included in the output name

    LOGGER.debug('RUNNING analysis function...')
    mapping, results = corine_stats_real_areas(
        input_polygons_path,
        input_path_rasters,
        input_path_headers,
        output_path,
        string_for_output_name)
    LOGGER.debug('RUNNING analysis function... DONE.')
    #LOGGER.info('These are the outputs: %s' % output_csvs)
    LOGGER.info('Finished.')
