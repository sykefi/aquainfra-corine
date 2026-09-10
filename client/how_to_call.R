#
# This script shows how the SYKE CORINE tool that is being
# developed in the scope of the AquaINFRA project can be
# called from inside R.
# The tools runs on a pygeoapi platform as a OGC processing service,
# which means it is available via a REST API and can be called via
# HTTP POST. In R, HTTP POST calls can be made using the httr library.
#
# Please be aware that our tools are currently under development and
# use a development server, which means they can be slow or temporarily
# be switched off or changed frequently.
#
#
# Merret Buurman, IGB Berlin, 2024-10-28
#

library(httr)
library(data.table)

## This is the process_id of your tool:
process_id <- "syke-corine-stats-real-areas"

## The input needs to be provided as list:
inputs = list(
    input_url_polygons = "https://example.com/exampledata/syke/sykeshape.zip"
)
print("Will send this as inputs:")
print(inputs)

## This is how to call the tool (don't change this):
url <- "https://example.com/pygeoapi"
endpoint <- paste0(url, "/processes/", process_id, "/execution")
response <- httr::POST(endpoint, body=list(inputs = inputs), encode="json", verbose())
print("Response to HTTP POST request:")
print(response)
result <- httr::content(response, as = "parsed", type = "application/json")
print("Result from HTTP POST request, parsed as JSON:")
print(result)

## This is one of the links to one of the CSV files:
print(result$outputs$csv_files_per_area$href[[1]])

## Read csv files (data.table::fread can read CSV from URLs):
# TODO: Rather put this in for-loop - this does not have to be four results, but depending on
# the number of areas in the input file!
d1 <- data.table::fread(result$outputs$csv_files_per_area$href[[1]])
d2 <- data.table::fread(result$outputs$csv_files_per_area$href[[2]])
d3 <- data.table::fread(result$outputs$csv_files_per_area$href[[3]])
d4 <- data.table::fread(result$outputs$csv_files_per_area$href[[4]])

## Now do your thing!
print("Content of example 1:")
print(d1)


