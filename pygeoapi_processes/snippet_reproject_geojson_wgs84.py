# This snippet allows to download GeoJSON, assuming it is WGS84.
# Then it reprojects it to 3067, as the SYKE tool wants that.
# And stores it again.
# And passes the path to that reprojected stored GeoJSON.

# But since January 2026, this does not seem to be necessary anymore.


        if input_url_geojson is not None:
            import requests
            import json
            input_path_polygons1 = output_dir+'/geojson_assume_wgs84.json'
            input_url_polygons1 = output_url+'/geojson_assume_wgs84.json'
            # Assuming WGS84...
            response = requests.get(input_url_geojson)
            response.raise_for_status()  # raises error if download failed
            feature = response.json()
            # Wrap into a FeatureCollection
            data = {
                "type": "FeatureCollection",
                "features": [feature]
            }
            with open(input_path_polygons1, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                LOGGER.debug(f'Stored input geojson from {input_url_geojson} to {input_path_polygons1}, accessible at {input_url_polygons1}.')

            import geopandas as gpd
            LOGGER.debug(f'Reading the WGS84 GeoJSON file from {input_path_polygons1}...')
            # Load the input GeoJSON (assumed WGS84 EPSG:4326)
            gdf = gpd.read_file(input_path_polygons1)
            LOGGER.debug(f'Done reading the WGS84 GeoJSON file from {input_path_polygons1}...')
            # Reproject to EPSG:3067
            LOGGER.debug('Reprojecting to 3067...')
            gdf_3067 = gdf.to_crs(epsg=3067)
            LOGGER.debug('Done reprojecting to 3067...')
            # Add custom CRS member (GeoJSON 2.0 removed the CRS member, but some tools still expect it)
            LOGGER.debug('Adding that to the GeoJSON as attribute...')
            geojson_dict = gdf_3067.__geo_interface__
            geojson_dict["crs"] = {"name": "urn:ogc:def:crs:EPSG::3067"}
            LOGGER.debug('Done adding that to the GeoJSON as attribute...')
            # Save to disk
            input_path_polygons = output_dir+'/geojson_3067.json'
            input_url_polygons = output_url+'/geojson_3067.json'
            with open(input_path_polygons, "w", encoding="utf-8") as f:
                json.dump(geojson_dict, f, ensure_ascii=False, indent=2)
                LOGGER.debug(f'Stored reprojected geojson to {input_path_polygons}, accessible at {input_url_polygons}.')


