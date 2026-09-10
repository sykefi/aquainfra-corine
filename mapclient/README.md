# Experimental map client

## How to deploy

We are using nginx.

Create directory:

```
mkdir /var/www/nginx/syke
```

Make nginx proxy to this directory:

```
vi /etc/nginx/sites-enabled/default
```

Make softlink to this file in the repo:

```
sudo ln -s /.../pygeoapi/pygeoapi/process/aquainfra_corine/mapclient /var/www/nginx/syke
```

And make sure to modify the URL in index.html to match your pygeoapi instance:

```
...
const base_url = "your-pygeoapi-instance.fi/pygeoapi";
...
```

Now you can test: https://yourserver.fi/syke/mapclient/index.html

* Try to draw a polygon on the map
* Click "Send"
* You should see some JSON appear in the field below the map after a while.

You are likely to run into a CORS error. The pygeoapi server has to allow you to
send POST requests to it. More info: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS/Errors/CORSAllowOriginNotMatchingOrigin

### Fixing CORS error server-side

You have to allow on the pygeoapi server side.

We assume that pygeoapi also runs behind a nginx reverse proxy.

Go to nginx config:

```
vi /etc/nginx/sites-enabled/default
```

Make sure these are set and match the hostname of the server that sends the POST requests to this pygeoapi instance:

```
add_header 'Access-Control-Allow-Origin' 'https://your-mapclient-server.fi' always;

```

