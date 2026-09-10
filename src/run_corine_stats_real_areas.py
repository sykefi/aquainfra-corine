import sys
import os
import zipfile
import requests
import logging

LOGGER = logging.getLogger(__name__)
# This does not have a format yet, just the message gets logged.
# We also did not specify log level yet, so only warnings get logged.


try:
    import aquainfra_corine.corine_stats_real_areas as corine_stats_real_areas
    LOGGER.warning('run: Cannot import "aquainfra_corine.corine_stats_real_areas"...')
except ModuleNotFoundError as e:
    LOGGER.warning('run: Importing "corine_stats_real_areas"...')
    import corine_stats_real_areas
    LOGGER.warning('run: Importing "corine_stats_real_areas"... DONE.')


def main():

    LOGGER.info('run: Received arguments: %s' % sys.argv)
    input_polygons_path = sys.argv[1]
    input_path_rasters = sys.argv[2]
    input_path_headers = sys.argv[3]
    output_path = sys.argv[4]
    randomstring = sys.argv[5]
    contact_email = sys.argv[6]

    ## Download input file

    # The tool uses geopandas.read_file() to read the polygons, so that could be
    # various types of file! Just if it is zipped, this will probably not work, so
    # we'll have to download and unzip previously...

    # Where will it be stored? Inside the container only!
    input_polygons_dir = '/in'
    if not os.path.exists(input_polygons_dir):
        os.makedirs(input_polygons_dir)

    # If user provided zipped shapefile:
    if input_polygons_path.startswith('http') and input_polygons_path.endswith('zip'):
        LOGGER.info('run: Downloading zipped shapefile...')
        input_polygons_path = download_zipped_shapefile(input_polygons_path, input_polygons_dir)

    # RASTER
    input_path_rasters = input_path_rasters.split(',')
    LOGGER.debug(f'Found {len(input_path_rasters)} rasters: {input_path_rasters}')



    LOGGER.debug('This file will be used for regions: %s' % input_polygons_path)
    LOGGER.debug('This is where headers are expected: %s' % input_path_headers)
    LOGGER.debug('This is where rasters are expected: %s' % input_path_rasters)
    LOGGER.debug('This is where we will store the outputs: %s' % output_path)

    LOGGER.info('run: Running corine function...')
    arearesults, output_csvs = corine_stats_real_areas.corine_stats_real_areas(
        input_polygons_path,
        input_path_rasters,
        input_path_headers,
        output_path,
        randomstring,
        contact_email)
    LOGGER.info('run: Running corine function... DONE.')

def download_zipped_shapefile(input_url_shapefile, input_polygons_dir):

    # Download file:
    LOGGER.info('Downloading input data file: %s' % input_url_shapefile)
    input_zipped_shp_path = '%s/downloaded.zip' % input_polygons_dir
    resp = requests.get(input_url_shapefile)
    if resp.status_code == 200:
        LOGGER.debug('Writing input shape file to: %s' % input_zipped_shp_path)
        with open(input_zipped_shp_path, 'wb') as myfile:
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    myfile.write(chunk)

        LOGGER.info('Unzipping file "%s" to "%s"' % (input_zipped_shp_path, input_polygons_dir))
        with zipfile.ZipFile(input_zipped_shp_path, 'r') as zip_ref:
            zip_ref.extractall(input_polygons_dir)
            LOGGER.info('Unzipped file to "%s"' % input_polygons_dir)

            # Find name of shapefile, which we dont control:
            # TODO I am sure there is a better way!
            for filename in os.listdir(input_polygons_dir):
                if filename.endswith('shp'):
                    input_polygons_path = '%s/%s' % (input_polygons_dir, filename)
                    #LOGGER.debug('This file will be used: %s' % input_polygons_path)
                    return input_polygons_path

    else:
        raise ProcessorExecuteError('Could not download input file (HTTP status %s): %s' % (resp.status_code, input_url_shapefile))





if __name__ == "__main__":

    # The docker output will be printed to the log of the main process, but there it adds again the whole format, so here we choose an easy format:
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)5s - %(message)s')
    #logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)5s - %(message)s')
    #logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)5s - %(message)s')
    logging.getLogger("rasterio").setLevel(logging.WARNING)
    main()


