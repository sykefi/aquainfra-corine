## SYKE Corine tool (Aquainfra)

## What is it about?

This process computes the size of the area in hectares (ha) covered by CORINE Land Cover (CLC) classes within user-defined polygonal regions. The analysis is based on harmonized Finnish or European CORINE raster datasets for the years 2000, 2006, 2012, and 2018. The harmonization aligns the class definitions across different CLC versions to ensure temporal consistency and comparability. This enables robust detection and quantification of land use and land cover changes over time. The Finnish CLC datasets are an enhanced national version with higher resolution and accuracy than the pan-European CLC data. The harmonization includes reclassification of original classes to a common schema, enabling reliable time-series analysis. The output supports various environmental assessments, such as tracking urban expansion, deforestation, or agricultural change. Please contact the Finnish Environment Institute (Syke, Sampsa.Koponen@syke.fi) for detailed documentation and support in applying this service.

Metadata to the Finnish Corine: https://b2share.eudat.eu/records/sxg8d-nbw81

Metadata to the European Corine: https://b2share.eudat.eu/records/x747j-fwr19 

## How to use this

The repository contains two python scripts for CORINE landcover: Finnish and European versions. Most things are readily built in: paths to harmonized CORINE rasters (Europe and Finnish), paths harmonized corine headers, and example input GIS-dataset, and example output-files. User only needs to follow the instructions and provide arbitrary input GIS-dataset

## Option 1 - (works)

Pull the repository:

```
git clone git@github.com:sykefi/aquainfra-corine.git
cd aquainfra_corine
```

Either create a python environment or a virtual environment and install the dependencies into it:

```
Python environment:
conda env create -f environment.yml
conda activate corine_tools

Virtual environment:
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

```
Change the paths of vector-datasets to your own paths corine_stats_real_areas.py and/or corine_europe_stats_areas. at ## INSERT THE INPUT POLYGON WITH "areaname"-ATTRIBUTE HERE
```


```
Running the scripts:

Finland:
python corine_stats_real_areas.py
Europe:
python corine_europe_stats_areas.py
```

Outputs will be generated either to example_outputs-folder or user-defined path.


IF you get connection errors try disabling the VPN and proxies



## Option 2 (Not sure if works)

There are several ways of using the contents of this repo:
* Option 1
* Running the Docker container
* Exposing the functionality via OGC API (so that it runs on a server and can be accessed via HTTP)


## Running the Docker container

There is a Dockerfile that allows you to build your own Docker image and run it locally.

How to build:

```
# git clone:
git clone <this repo>

# build:
cd aquainfra_corine
today=$(date '+%Y%m%d')
docker build -t syke_corine:${today} .
```

The tools expects the following files and directories to exist:

* `./example_inputs/aquainfra_catchment_areas.shp`

The Finland script expects this:

* `./example_inputs/Harmonized_Corine_level1_headers.csv`
* `./example_inputs/Harmonized_Corine_level4_headers.csv`

The Europe script expects this:

* `./example_inputs/harmonized_corine_europe_headers_2018.csv`


How to run the Europe script:

```
# define the URLs to the input rasters (Cloud Optimized GeoTIFF files):
rasters="https://aquainfra-syke.a3s.fi/europe_clc_cog_raster/CLC2000ACC_V2018_20_cog.tif",
        "https://aquainfra-syke.a3s.fi/europe_clc_cog_raster/CLC2006ACC_V2018_20_cog.tif",
        "https://aquainfra-syke.a3s.fi/europe_clc_cog_raster/CLC2012ACC_V2018_20_cog.tif",
        "https://aquainfra-syke.a3s.fi/europe_clc_cog_raster/CLC2018ACC_V2018_20_cog.tif"
# run:
docker run \
  --name testcontainer \
  -e 'SCRIPT=run_corine_europe_stats_areas.py' \
  -v "./example_inputs/:/in_shp" \
  -v "./example_inputs/:/in_headers" \  
  -v "./example_outputs:/out" \
  syke_corine:20260219 \
  "/in_shp/aquainfra_catchment_areas.shp" ${rasters} "/in_headers/" "/out" "blah123" "contact@example.fi"
```

How to run the Finland script:

```
# define the URLs to the input rasters (VRT files):
rasters= "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2000_finland_harmonized_20m_cog.tif",
        "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2006_finland_harmonized_20m_cog.tif",
        "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2012_finland_harmonized_20m_cog.tif",
        "https://aquainfra-syke.a3s.fi/finland_clc_cog_raster/CLC2018_finland_harmonized_20m_cog.tif"

# run:
docker run \
  --name testcontainer \
  -e 'SCRIPT=run_corine_stats_real_areas.py' \
  -v "./example_inputs/:/in_shp" \
  -v "./example_inputs/:/in_headers" \
  -v "./example_outputs:/out" \
  syke_corine:20260219 \
  "/in_shp/aquainfra_catchment_areas.shp" ${rasters} "/in_headers" "/out" "blah123" "contact@example.fi"
```


Then the result files `corine_stats_real_areas_<area>.csv` should now be inside `/var/www/nginx/download/out`.


## OGC processing services

In the EU-funded project [AquaINFRA](https://aquainfra.eu/)
we tested running the MITgcm model on a server, where it can be
called via HTTP by a user via the so-called OGC API
(Open Geospatial Consortion, see [here](https://ogcapi.ogc.org/)),
using the platform [pygeoapi](https://pygeoapi.io/).

For this, look at the README in the directory `pygeoapi_processes`.


## METADATA

Developed by: Finnish Environment Institute (Syke), Finland
Original authors: Alkio Eero, Bruun Eeva, Buurman Merret
Project: AquaINFRA – Infrastructure for Marine and Inland Water Research
Grant agreement: 101094434

Source repository: https://github.com/sykefi/aquainfra-corine
Software version: v1.0.0
DOI: 10.5281/zenodo.22792055
License: Creative Commons Attribution 4.0 International


Contact:
Finnish Environment Institute (Syke, Sampsa.Koponen@syke.fi)

Developed in AquaINFRA project. This project has received funding from the European Commission's Horizon Europe Research and Innovation programme under grant agreement No 101094434.

## TODO

Update the OGC processing and docker instructions. Upload the CORINE headers online to be used similarly as raster paths. Create a tool for user to draw the input polygons and connect to scripts. 
