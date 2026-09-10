
# How to deploy as OGC service on pygeoapi

**Note: This is all work in progress, the code may change faster than this documentation...**

## Preparations

* You need a pygeoapi instance running! Please deploy it according to the pygeoapi documentation.
* You need to have docker installed

## Deploy the function(s) contained in this repo


* Go into pygeoapi's processes directory: `cd pygeoapi/pygeoapi/processes`
* Clone this repo there.
* Store the static input data (header files, rasters)
* Build the docker image (see instructions on main README page)
* Add the service to the `plugin.py` (under `'process'`): `'SykeCorineProcessor': 'pygeoapi.process.aquainfra_corine.pygeoapi_processes.process_corine_stats_real_areas.SykeCorineProcessor',`
* Add the service to `pygeoapi-config.yml` (under `resources:`):

```
    syke-corine-stats-real-areas:
        type: process
        processor:
            name: SykeCorineProcessor
```

* Now reinstall pygeoapi (so it knows about these recently added services), depending on your pygeoapi installation.
* Now re-generate the `openapi.yml` file, according to the pygeoapi docs
* Now restart your pygeoapi installation


### Configuration

* Create a `config.json` inside the pygeoapi base directory, containing the following items:

```
{
    "download_dir": "/var/www/nginx/download/",
    "download_url": "https://aquainfra.ogc.igb-berlin.de/download/",
    "docker_executable": "/usr/bin/docker",
    "syke": {
        "service_contact_email": "test@test.fi",
        "inputs_static_rasters_path": "/var/www/nginx/download/readonly/",
        "inputs_static_headers_path": "/var/www/nginx/download/readonly/"
    }
}
```

where...

* `inputs_static_rasters_path`: directory where the service can find the input rasters (tif)
* `inputs_static_headers_path`: directory where the service can find the input header files (csv)
* `download_dir`: directory where to store the results so users can download the results! Depends on your server settings...
* `download_url`: the URL to give back to users, where they can download the results stored in 'download_dir'
* `service_contact_email`: who users should contact in case of errors!


**Notes:**

* You may have to make sure that pygeoapi is allowed to access the input data, and write to the output data directory.
* You need to put the input rasters you want to run the analysis on into: `/opt/aquainfra_inputs/CORINE`.
* The service should be available on localhost (and possibly from outside):

```
curl -X POST 'http://localhost:5000/processes/syke-corine-stats-real-areas/execution' \
--header 'Content-Type: application/json' \
--data '{
    "inputs": {
        "input_url_shapefile": "https://example.fi/download/some-shape-file.zip"
    }
}'
```

(If this example is not up to date, a more up to date example should be located in the respective pygeoapi process file: https://github.com/AquaINFRA/aquainfra_corine/blob/aquabranch/pygeoapi_processes/first_process.py)


## Changes to services...

* If the function code changed, just go to `/opt/.../pygeoapi/pygeoapi/process/syke/aquainfra_corine` and pull the latest changes.
* If any config changed, change `vi /opt/.../pygeoapi/config.json`
* If those header csv files change, no update is needed, as the config tells pygeoapi to look for them inside `/opt/.../pygeoapi/pygeoapi/process/syke/aquainfra_corine/` (see `vi /opt/.../pygeoapi/config.json`).
* If the input rasters change, update them here: `/opt/aquainfra_inputs/CORINE/` (see `vi /opt/.../pygeoapi/config.json`).
* If the input shapefile changes, it is the user/client who has to update them - but as a convenience and for testing change it in `/var/www/nginx/referencedata/syke/`, so it can be used from https://testserver.de/referencedata/syke/shape_aquainfra_dis_4.zip
