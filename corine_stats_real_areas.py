# -*- coding: utf-8 -*-
"""
Created on Tue Apr 16 12:06:34 2024

Modified by Merret Buurman, IGB, February 2025

Modified by Eero Alkio, Syke, 12th February 2026

"""

#-*- coding: utf-8 -*-
#conda create --name statcomp python=3.11
#conda activate statcomp
#conda install -c conda-forge rasterstats=0.19.0  
#conda install -c conda-forge geopandas=0.9.0


from rasterstats import zonal_stats
import os, glob
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
    
    ## Getting the raster crs
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
        ## Previously: Allow for unnamed areas:
        #try:
        #    areaname = area.areaname
        #except AttributeError as e:
        #    LOGGER.warning('Area has to attribute areaname.')
        #    areaname = 'unnamed_area_%s' % i
        #
        #LOGGER.debug('Area %s: %s' % (i, areaname))

        ## Added areaname check EA
        if "areaname" not in areas.columns:
            LOGGER.error('Area %s has no areaname attribute!' % input_polygons_path)
            raise ValueError('Area in file %s has no areaname attribute!' % input_polygons_path)

        areaname = area.areaname
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

        # Make ASCII filename:
        areaname_ascii = (c for c in areaname if 0 < ord(c) < 127)
        areaname_ascii = ''.join(areaname_ascii)
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
corine_stats_real_areas_<areaname>_<string_for_output_name>.csv

For example:
corine_stats_real_areas_Kerava_test123.csv
corine_stats_real_areas_Vantaa_test123.csv
corine_stats_real_areas_Pitkkoski_test123.csv

'''

if __name__ == "__main__":

    # Tell python to log to console, at debug level:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)5s - %(message)s')
    # Alternatively, to file:
    #logging.basicConfig(level=logging.DEBUG, filename='corine_stats_real_areas.log', format='%(asctime)s - %(name)s - %(levelname)5s - %(message)s')

    # Where are the inputs stored?
    input_polygons_path = "./example_inputs/aquainfra_catchment_areas.shp"
    input_path_headers = "./example_inputs/" # .csv headers have to be in here
    ## Previously: Used locally stored rasters:
    #input_path_rasters = "./example_rasters/" # .tif rasters have to be in here
    ## Now: These input rasters should be implemented in the process-file
    input_path_rasters = ["https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2000_finland_harmonized_20m_cog.tif",
"https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2006_finland_harmonized_20m_cog.tif",
"https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2012_finland_harmonized_20m_cog.tif",
"https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2018_finland_harmonized_20m_cog.tif"
]
    # Where will the outputs be stored?
    output_path = "./outputs"
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
