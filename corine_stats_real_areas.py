# -*- coding: utf-8 -*-
"""
Created on Tue Apr 16 12:06:34 2024

Modified by Merret Buurman, IGB, February 2025

Modified by Eero Alkio, Syke, 12th February 2026 and finalized 9/2026 

"""

from rasterstats import zonal_stats
import os, glob, re
import geopandas as gpd
import pandas as pd
import datetime
import logging
import rasterio


LOGGER = logging.getLogger(__name__)

def corine_stats_real_areas(input_polygons_path, input_path_rasters, input_path_headers, output_path, string_for_output_name, contact_email=None):

    ## Input rasters as list of .vrt urls
    rasters = sorted(input_path_rasters)

    # Warn if no rasters
    if len(rasters) == 0:
        LOGGER.error('No input vrt paths incdluded in found in: %s' % input_path_rasters)
        if contact_email is None:
            raise ValueError('No input rasters found. Please check in input vrt list: %s' % input_path_rasters)
        else:
            # If this is run on an AquaINFRA server, users cannot check the input directory, but have to contact someone:
            raise ValueError('No input rasters found. Please contact service owner (%s)' % contact_email)
        
    # Polygons and rasters must be in the same CRS
    areas = gpd.read_file(input_polygons_path)
    
    ## Getting the raster crs from the first input raster (These should all have the same CRS)
    with rasterio.open(input_path_rasters[0]) as src:
        raster_crs = src.crs
    
    ## Raising error if no CRS is defined. 
    if areas.crs is None:
        print(f"Missing crs for polygon {input_polygons_path}")
        raise ValueError("Missing CRS - the input polygon file must have a defined CRS")
        
    ## Reprojecting vector data to same crs as the first input raster
    if areas.crs != raster_crs:
        areas = areas.to_crs(raster_crs)

    # Test if output path exist - otherwise no need to start the computation!
    if not os.path.exists(output_path):
        raise ValueError("Directory %s does not exist!" % output_path)
    if not os.path.isdir(output_path):
        raise ValueError("Directory %s is not a directory!" % output_path)

    # Read land cover classes for Harmonized Corine level1 and level4
    ## Finnish harmonization mapping
    in_corineheader0 = '%s/Harmonized_Corine_level4_headers.csv' % input_path_headers
    in_corineheader1 = '%s/Harmonized_Corine_level1_headers.csv' % input_path_headers

    corineheader  = pd.read_csv(in_corineheader0, sep=';')
    corineheader1 = pd.read_csv(in_corineheader1, sep=';')

    # Collect output paths:
    output_csvs = []

    # Iterate over catchments areas
    i = 0
    LOGGER.debug('Iterating over the areas...')
    for idx, area in areas.iterrows():
        i += 1
        ## Fall back to an auto-generated name if areaname is missing or empty EA
        has_areaname = "areaname" in areas.columns and pd.notna(area.get("areaname")) and str(area.get("areaname")).strip() != ""
        if has_areaname:
            areaname = area.areaname
        else:
            areaname = "area_%s" % i
            LOGGER.warning('Area %s in file %s has no areaname attribute - using fallback name "%s" instead.' % (i, input_polygons_path, areaname))
            area["areaname"] = areaname

        LOGGER.debug('Area %s: %s' % (i, areaname))
        #LOGGER.debug(area) # show the attributes from the shapefile!
        
        area = area[['areaname', 'geometry']]
        arearesults = pd.DataFrame()

        # Iterate over Corine years
        j = 0
        LOGGER.debug('Now iterate over the %s rasters for area %s...' % (len(rasters), areaname))
        for raster in rasters:
            j += 1
            rastername = os.path.basename(raster).replace('.tif','')
            raster_year = rastername[3:7]
            LOGGER.debug('Raster %s (for area %s): %s' % (j, areaname, rastername))

            ## Extracting year from raster

            ## Storing raster basename
            area_data = area.copy()
            area_data['Year'] = raster_year
            area_data['Raster'] = rastername

            # Extract land use pixel counts per classes

            zs = zonal_stats([area_data.geometry], raster=raster, categorical=True)
            # One column per raster category, and pixel count as value
            
            
            stats = pd.DataFrame(zs).fillna(0)
            #LOGGER.debug('Stats: %s' % stats_hectare)
            ## Finnish CLC has 20m resolution, converting to hectare
            stats_hectare = stats * 0.04

            # convert raw raster values to corine level 4 class numbers
            mapping = corineheader.set_index('Value')['Level4'].to_dict()
            stats_hectare = stats_hectare.rename(columns=mapping)
            # Aggregate level 4 areas to level 1 corine classes

            ## pandas groupby - axis is deprecated in newer pandas versions
            stats_hectare2 = (
                stats_hectare.rename(columns=lambda x: int(x)//1000)
                .T.groupby(level=0)
                .sum().astype(int)
                .T
            )
            # Combine areametadata with statistics
            results = pd.concat([area_data, stats_hectare2.iloc[0]], axis=0)

            df = pd.DataFrame(results.drop('geometry'))

            # convert corine class numbers to their English names
            df = df.rename(corineheader1.set_index('Value')['Level1Eng'])
            df = df.rename(corineheader.set_index('Level4')['Level4Eng'])

            # Combine years
            arearesults = pd.concat([arearesults, df], axis=1)

        arearesults = arearesults.T.set_index('Year')
        
        LOGGER.debug('Done iterating over rasters for this area... (%s)' % areaname)
        #LOGGER.debug(arearesults) # This is long!

        # Make ASCII, filename-safe name: drop non-ASCII chars, replace the rest of unsafe chars with underscores
        areaname_ascii = ''.join(c for c in areaname if 0 < ord(c) < 127)
        areaname_ascii = re.sub(r'[^A-Za-z0-9._-]+', '_', areaname_ascii).strip('_')
        if not areaname_ascii:
            areaname_ascii = 'area_%s' % i
        LOGGER.debug('Area name in ASCII: BEFORE: %s, AFTER: %s' % (areaname, areaname_ascii))

        filename = 'finland_corine_stats_real_areas_%s_%s.csv' % (areaname_ascii, string_for_output_name)

        filepath = '%s/%s' % (output_path, filename)

        # Store to CSV:
        LOGGER.debug('Storing to: %s' % filepath)

        arearesults.to_csv(filepath, sep=';', float_format="%.2f")

        # Create result dict:
        output_csvs.append({
           "area_name": areaname_ascii,
           "area_name_specialchars": areaname,
           "file_name": filename,
           "file_path": filepath
        })


    return arearesults, output_csvs

'''
To run this code locally, define the paths for inputs and outputs here.

The outputs will be one csv file per area, named as follows:
finland_stats_real_areas_<areaname>_<string_for_output_name>.csv

For example:
finland_corine_stats_real_areas_Kerava.csv
finland_corine_stats_real_areas_Vantaa.csv
finland_corine_stats_real_areas_Pitkkoski.csv

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

    ## Now: Harmonized Corine rasters for Finland
    input_path_rasters = [
        "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2000_finland_harmonized_20m_cog.tif",
        "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2006_finland_harmonized_20m_cog.tif",
        "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2012_finland_harmonized_20m_cog.tif",
        "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2018_finland_harmonized_20m_cog.tif"
    ]
    ## Modify the output path if needed (csv-files)
    output_path = "./example_outputs"
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    string_for_output_name = datetime.datetime.today().strftime('%Y-%m-%d')  # will be included in the output name

    LOGGER.debug('RUNNING analysis function...')
    results, output_csvs = corine_stats_real_areas(
        input_polygons_path,
        input_path_rasters,
        input_path_headers,
        output_path,
        string_for_output_name)
    LOGGER.debug('RUNNING analysis function... DONE.')
    LOGGER.info('These are the outputs: %s' % output_csvs)
    LOGGER.info('Finished.')
