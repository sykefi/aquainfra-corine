import logging

from pygeoapi.process.base import BaseProcessor, ProcessorExecuteError
import os
import json
import subprocess
import pandas as pd


LOGGER = logging.getLogger(__name__)

'''
# Input: Zipped shapefile (and VRT layers)
# TESTED 2026-02-19
curl -X POST https://${PYSERVER}/processes/corine-stats-real-areas-finland/execution \
--header 'Content-Type: application/json' \
--data '{
    "inputs": {
        "input_url_polygons": "https://aquainfra.ogc.igb-berlin.de/exampledata/syke/corine/sykeshape.zip"
    }
}'

# Input: GeoJSON file (reprojected to EPSG::3067) (and VRT layers)
# TESTED 2026-02-19
curl -X POST https://${PYSERVER}/processes/corine-stats-real-areas-finland/execution \
--header 'Content-Type: application/json' \
--data '{
    "inputs": {
        "input_url_polygons": "https://aquainfra.ogc.igb-berlin.de/exampledata/syke/aquainfra_catchment_areas.geojson"
    }
}'

# Input: GeoJSON, passed directly. WGS84.
# Note: If you leave out the explicit specification of the CRS, the results seem to be the same:
# TESTED 2026-02-19
curl -X POST https://${PYSERVER}/processes/corine-stats-real-areas-finland/execution \
--header 'Content-Type: application/json' \
--data '{
    "inputs": {
        "input_geojson": {
            "type": "FeatureCollection",
            "name": "test_smaller",
            "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
            "features": [
                { "type": "Feature", "properties": { "id": 0, "areaname": "dummytestarea1", "bla": "blabla" }, "geometry": { "type": "MultiPolygon", "coordinates": [ [ [ [ 24.81653120257662, 60.527120967406184 ], [ 24.864441337996166, 60.580458347900688 ], [ 25.047419437756226, 60.567301587155775 ], [ 25.056071225665772, 60.486711783112462 ], [ 24.863705379133737, 60.432614226118567 ], [ 24.81653120257662, 60.527120967406184 ] ] ] ] } },
                { "type": "Feature", "properties": { "id": 1, "areaname": "dummytestarea2", "bla": "blablabla" }, "geometry": { "type": "MultiPolygon", "coordinates": [ [ [ [ 24.80461120659341, 60.492195890484425 ], [ 24.878940281769378, 60.402821687100236 ], [ 24.779035754945664, 60.351443462584129 ], [ 24.61133966426646, 60.390779223391824 ], [ 24.647769619581187, 60.477318962307905 ], [ 24.647769619581187, 60.477318962307905 ], [ 24.80461120659341, 60.492195890484425 ] ] ] ] } }
            ]
        }
    }
}'

# Experimental:
# Input: GeoJSON, passed directly - but only ONE Feature --> returns JSON directly, not link to CSV file!
# TESTED 2026-02-19
curl -X POST https://${PYSERVER}/processes/corine-stats-real-areas-finland/execution \
--header 'Content-Type: application/json' \
--data '{
    "inputs": {
        "input_geojson": {
            "type": "FeatureCollection",
            "name": "test_smaller",
            "features": [
                { "type": "Feature", "properties": { "id": 0, "areaname": "dummytestarea1", "bla": "blabla" }, "geometry": { "type": "MultiPolygon", "coordinates": [ [ [ [ 24.81653120257662, 60.527120967406184 ], [ 24.864441337996166, 60.580458347900688 ], [ 25.047419437756226, 60.567301587155775 ], [ 25.056071225665772, 60.486711783112462 ], [ 24.863705379133737, 60.432614226118567 ], [ 24.81653120257662, 60.527120967406184 ] ] ] ] } }
            ]
        }
    }
}'

'''

# Process metadata and description
# Has to be in a JSON file of the same name, in the same dir!
script_title_and_path = __file__
metadata_title_and_path = script_title_and_path.replace('.py', '.json')
PROCESS_METADATA = json.load(open(metadata_title_and_path))



class SykeCorineFinlandProcessor(BaseProcessor):

    def __init__(self, processor_def):
        super().__init__(processor_def, PROCESS_METADATA)
        self.supports_outputs = True
        self.job_id = None
        self.process_id = self.metadata["id"]
        self.image_name = 'syke_corine:20260303'
        self.script_name = 'run_corine_stats_real_areas.py'

        # Set config:
        config_file_path = os.environ.get('AQUAINFRA_CONFIG_FILE', "./config.json")
        with open(config_file_path, 'r') as config_file:
            config = json.load(config_file)
            self.docker_executable = config["docker_executable"]
            self.download_dir = config["download_dir"].rstrip('/')
            self.download_url = config["download_url"].rstrip('/')
            self.contact_email = config['syke']['service_contact_email']
            # Header files are static:
            # TODO: Headers into Docker image? Or mount and pass like this, through config?
            self.input_path_headers = config['syke']['inputs_static_headers_path'].rstrip('/')

    def __repr__(self):
        return f'<SykeCorineFinlandProcessor> {self.name}'


    def set_job_id(self, job_id: str):
        self.job_id = job_id


    def execute(self, data, outputs=None):
        LOGGER.info("Starting to compute CORINE process results...")

        ###################
        ### User inputs ###
        ###################

        input_url_polygons = data.get('input_url_polygons', None)
        input_geojson = data.get('input_geojson', None)
        #input_urls_rasters = data.get('input_urls_rasters', None)

        # Check inputs...
        if input_url_polygons is None and input_geojson is None:
            raise ProcessorExecuteError('Please provide either a link to a zipped shapefile or to a geojson file or provide geojson directly.')
        elif input_url_polygons is not None and input_geojson is not None:
            raise ProcessorExecuteError('Not sure which one to use...')
        #if input_urls_rasters is None:
        #    raise ProcessorExecuteError("Missing input parameter 'input_urls_rasters': Please provide a list of links to cloud-optimized input rasters.")

        #######################
        ### Inputs, outputs ###
        #######################

        # Where to store output data
        # Note: We don't know the number of output csv files yet, so we cannot create
        # the download links yet...
        output_dir = f'{self.download_dir}/out/{self.process_id}/job_{self.job_id}'
        output_url = f'{self.download_url}/out/{self.process_id}/job_{self.job_id}'
        os.makedirs(output_dir)

        # In case GeoJSON is passed directly, we create a file that we can then
        # use as input for the tool. We provide that file as a URL, not as a path
        # in the file system, so we don't have to mount it.
        if input_url_polygons is None and input_geojson is not None:

            input_path_polygons = output_dir+'/geojson.json'
            input_url_polygons = output_url+'/geojson.json'

            LOGGER.debug('Writing input geojson file to: %s' % input_path_polygons)
            with open(input_path_polygons, 'w') as myfile:
                json.dump(input_geojson, myfile)
                LOGGER.info('Wrote input GeoJSON to: %s, will be accessible at %s' % (input_path_polygons, input_url_polygons))


        ######################################
        ### Run corine script in container ###
        ######################################

        # Hard-coded rasters:
        input_urls_rasters = [
            "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2000_finland_harmonized_20m_cog.tif",
            "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2006_finland_harmonized_20m_cog.tif",
            "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2012_finland_harmonized_20m_cog.tif",
            "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2018_finland_harmonized_20m_cog.tif"
        ]
        input_urls_rasters = ','.join(input_urls_rasters)


        # Assemble parameters that will be passed on to python script inside docker:
        randomstring = self.job_id
        python_args = [input_url_polygons, input_urls_rasters, self.input_path_headers, output_dir, randomstring, self.contact_email]

        # Run docker container:
        returncode, stdout, stderr, user_err_msg = run_docker_container(
            self.docker_executable,
            self.image_name,
            self.script_name,
            output_dir,
            self.input_path_headers,
            python_args
        )

        if not returncode == 0:
            user_err_msg = "no message" if len(user_err_msg) == 0 else user_err_msg
            err_msg = 'Running docker container failed: %s' % user_err_msg
            raise ProcessorExecuteError(user_msg = err_msg)


        #############################
        ### Prepare response JSON ###
        #############################

        # Iterate over files stored in result path:
        output_csvs = []
        for filename in os.listdir(output_dir):
            #filename = os.fsdecode(filename)
            if filename.endswith(".csv"): 
                LOGGER.debug('Returning this csv file: %s' % filename)
                output_csvs.append(output_dir.rstrip('/')+'/'+filename)
            else:
                LOGGER.debug('Not returning this non-csv file: %s' % filename)

        # Convert result to JSON (maybe):
        # If the input was passed directly as GeoJSON in the HTTP payload, we assume that
        # the client also wants the results back directly (as GeoJSON), e.g. if the request
        # is coming from the map client.
        # TODO: It would probably be better to be able to tell the tool whether we want a csv
        # or GeoJSON or a dataframe back, instead of writing the tool to CSV and then reading
        # it back in at this place.
        if input_geojson is not None and len(output_csvs) == 1:
            result_df = pd.read_csv(output_csvs[0], sep=";", index_col=0)
            result_json = result_df.to_dict()
            LOGGER.info('This will be the response: %s' % result_json)
            return 'application/json', result_json

        # Make download links for all of them:
        output_links = []
        for item in output_csvs:
            downloadlink = item.replace(self.download_dir, self.download_url)
            output_links.append(downloadlink)

        # Prepare JSON object that will be returned to user:
        response_object = {
            "outputs": {
                "csv_files_per_area": {
                    "title": self.metadata['outputs']['csv_files_per_area']['title'],
                    "description": self.metadata['outputs']['csv_files_per_area']['description'],
                    "href": output_links
                }
            }
        }

        # Return link to file:
        LOGGER.info('This will be the response: %s' % response_object)
        return 'application/json', response_object


# TODO: Improve run_docker_container method, e.g. copying the way it is done in HEAT or specleanr!
def run_docker_container(
        docker_executable,
        image_name,
        script_name,
        output_dir,
        readonly_dir,
        script_args
    ):
    LOGGER.debug('Prepare running docker container')
    LOGGER.debug('Received args: %s' % script_args)

    # Create container name
    # Note: Only [a-zA-Z0-9][a-zA-Z0-9_.-] are allowed
    # TODO: Use job-id?
    container_name = "%s_%s" % (image_name.split(':')[0], os.urandom(5).hex())

    # Define paths inside the container
    container_readonly = '/readonly'
    container_out = '/out'

    # Define local paths (on host)
    local_readonly = readonly_dir
    local_out = output_dir

    # Replace paths in args:
    sanitized_args = []
    for arg in script_args:
        newarg = arg
        if local_out in arg:
            newarg = arg.replace(local_out, container_out)
            LOGGER.debug("Replaced argument %s by %s..." % (arg, newarg))
        elif local_readonly in arg:
            newarg = arg.replace(local_readonly, container_readonly)
            LOGGER.debug("Replaced argument %s by %s..." % (arg, newarg))
        sanitized_args.append(newarg)

    # Prepare container command
    # (mount volumes etc.)
    docker_args = [
        docker_executable, "run",
        "--rm",
        "--name", container_name,
        "-e", f"SCRIPT={script_name}",
        "-v", f"{local_readonly}:{container_readonly}",
        "-v", f"{local_out}:{container_out}",
        image_name
    ]
    docker_command = docker_args + sanitized_args
    LOGGER.debug('Docker command: %s' % docker_command)
    
    # Run container
    try:
        LOGGER.debug('Start running docker container')
        result = subprocess.run(docker_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = result.stdout.decode()
        stderr = result.stderr.decode()
        LOGGER.debug('Finished running docker container')
        log_docker_outputs(stdout, stderr)
        return result.returncode, stdout, stderr, "no error"

    except subprocess.CalledProcessError as e:
        returncode = e.returncode
        stdout = e.stdout.decode()
        stderr = e.stderr.decode()
        LOGGER.error('Failed running docker container (exit code %s)' % returncode)
        log_docker_outputs(stdout, stderr)
        user_err_msg = get_error_message_from_docker_stderr(stderr)
        return returncode, stdout, stderr, user_err_msg


def log_docker_outputs(stdout, stderr):
    for line in stdout.split('\n'):
        if line:
            LOGGER.debug('Docker stdout: %s' % line)
    for line in stderr.split('\n'):
        if line:
            LOGGER.debug('Docker stderr: %s' % line)


def get_error_message_from_docker_stderr(stderr):
    '''
    We would like to return meaningful messages to users.
    '''
    user_err_msg = ""
    for line in stderr.split('\n'):

        # Skip empty lines:
        if not line:
            continue

        # R error messages may start with the word "Error"
        if "ERROR" in line or "Error" in line:
            #LOGGER.debug('### Found explicit error line: %s' % line.strip())
            if "raise" in line:
                # The traceback contains the line that raises the error, so we
                # would return that to the user...
                # TODO: Do we have to add this to other run_docker too?
                pass
            else:
                user_err_msg += line.strip()

        else:
            #LOGGER.debug('### Do not pass back to user: %s' % line.strip())
            pass

    LOGGER.info(f'Error message for user: {user_err_msg}')
    return user_err_msg

