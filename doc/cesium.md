# Cesium Installation

Here's a short version how to build Cesium component of this software:

```
cd cesium
npm install
npm run-script build
npm run-script run
```

To build release version, do:

```
npm run build
```

and then you should get the package in dist/ directory.

Upgrading to latest cesium:

```
npm install cesium
```

Note: the labels will be shown as random garbage if firefox's resistFingerprinting feature is turned on.

## Development deployment

1. Start Flask as usual:

```shell
cd server
source venv/bin/activate
./aquarius-web.py
```

This will open http://localhost:8080. Most of the UI is accessible here, except the Cesium visualization.

2. In another console:

```shell
cd cesium
npm install
npm run-script run
```

This will open http://localhost:9000. Here's only the Cesium visualization is available.
