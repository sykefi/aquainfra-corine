# Use an official Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable for GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Create a working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the scripts to be called by the OGC processes:
COPY ./corine_stats_real_areas.py /src/
COPY ./corine_europe_stats_areas.py /src/
COPY src /src
WORKDIR /src

# Run the script
# Now that we have two functions in the same docker, the user has to
# pass the script name as env var, and entrypoint will call the script.
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Optional default script
ENV SCRIPT="run_corine_europe_stats_areas.py"
# Optional default args
CMD ["/in_shp/aquainfra_catchment_areas.shp", "urls1.cog,url2.cog,url3.cog", "/in_headers", "/out", "randomstring123", "contact@example.fi"]

# Example build command:
#today=$(date '+%Y%m%d')
#docker build -t syke_corine:${today} .

# docker run -v "/var/www/nginx/download/in:/in" -v "/var/www/nginx/download/readonly:/readonly" -v "/var/www/nginx/download/out:/out" syke_corine:20250509 "/in/aquainfra_catchment_areas.shp" "/readonly/" "/readonly/" "/out" "blah123" "contact@example.fi"
