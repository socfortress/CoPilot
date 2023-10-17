<template>
	<mgl-map :center="center" :zoom="zoom" :attribution-control="false">
		<mgl-frame-rate-control />
		<mgl-fullscreen-control />
		<mgl-attribution-control />
		<mgl-navigation-control />
		<mgl-scale-control />
		<mgl-geolocation-control />
		<mgl-style-switch-control :map-styles="mapStyles" :position="controlPosition" />
		<mgl-marker :coordinates="markerCoordinates" color="#cc0000" :scale="0.5" />
		<mgl-geo-json-source source-id="geojson" :data="geoJsonSource">
			<mgl-line-layer layer-id="geojson" :layout="layout" :paint="paint" />
		</mgl-geo-json-source>
		<mgl-vector-source source-id="libraries" :tiles="librariesSourceTiles">
			<mgl-circle-layer layer-id="libraries" source-layer="libraries" :paint="librariesLayerCirclesPaint" />
		</mgl-vector-source>
	</mgl-map>
</template>

<script lang="ts" setup>
/*eslint  @typescript-eslint/no-unused-vars: "off"*/
import {
	MglMap,
	MglDefaults,
	useMap,
	MglCircleLayer,
	MglVectorSource,
	MglLineLayer,
	MglGeoJsonSource,
	MglMarker,
	MglStyleSwitchControl,
	MglButton,
	MglCustomControl,
	MglGeolocationControl,
	MglScaleControl,
	MglNavigationControl,
	MglAttributionControl,
	MglFullscreenControl,
	MglFrameRateControl
} from "vue-maplibre-gl"
import type { StyleSwitchItem } from "vue-maplibre-gl"
import type { LngLatLike, LineLayerSpecification, CircleLayerSpecification } from "maplibre-gl"
import type { Feature } from "geojson"
import { ref } from "vue"

enum Position {
	TOP_LEFT = "top-left",
	TOP_RIGHT = "top-right",
	BOTTOM_LEFT = "bottom-left",
	BOTTOM_RIGHT = "bottom-right"
}

MglDefaults.style = "https://api.maptiler.com/maps/streets/style.json?key=cQX2iET1gmOW38bedbUh"

const mapStyles = [
	{
		name: "Streets",
		label: "Streets",
		style: "https://api.maptiler.com/maps/streets/style.json?key=cQX2iET1gmOW38bedbUh"
	},
	{ name: "Basic", label: "Basic", style: "https://api.maptiler.com/maps/basic/style.json?key=cQX2iET1gmOW38bedbUh" },
	{
		name: "Bright",
		label: "Bright",
		style: "https://api.maptiler.com/maps/bright/style.json?key=cQX2iET1gmOW38bedbUh"
	},
	{
		name: "Satellite",
		label: "Satellite",
		style: "https://api.maptiler.com/maps/hybrid/style.json?key=cQX2iET1gmOW38bedbUh"
	},
	{
		name: "Voyager",
		label: "Voyager",
		style: "https://api.maptiler.com/maps/voyager/style.json?key=cQX2iET1gmOW38bedbUh"
	},
	{
		name: "watercolor",
		label: "Water color",
		style: {
			version: 8,
			sources: {
				"raster-tiles": {
					type: "raster",
					tiles: ["https://stamen-tiles.a.ssl.fastly.net/watercolor/{z}/{x}/{y}.jpg"],
					tileSize: 256,
					attribution:
						'Map tiles by <a target="_top" rel="noopener" href="http://stamen.com">Stamen Design</a>, under <a target="_top" rel="noopener" href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a target="_top" rel="noopener" href="http://openstreetmap.org">OpenStreetMap</a>, under <a target="_top" rel="noopener" href="http://creativecommons.org/licenses/by-sa/3.0">CC BY SA</a>'
				}
			},
			layers: [
				{
					id: "simple-tiles",
					type: "raster",
					source: "raster-tiles",
					minzoom: 0,
					maxzoom: 22
				}
			]
		}
	}
] as StyleSwitchItem[]

const geoJsonSource = ref({
	type: "Feature",
	geometry: {
		type: "Polygon",
		coordinates: [
			[
				[-67.13734351262877, 45.137451890638886],
				[-66.96466, 44.8097],
				[-68.03252, 44.3252],
				[-69.06, 43.98],
				[-70.11617, 43.68405],
				[-70.64573401557249, 43.090083319667144],
				[-70.75102474636725, 43.08003225358635],
				[-70.79761105007827, 43.21973948828747],
				[-70.98176001655037, 43.36789581966826],
				[-70.94416541205806, 43.46633942318431],
				[-71.08482, 45.3052400000002],
				[-70.6600225491012, 45.46022288673396],
				[-70.30495378282376, 45.914794623389355],
				[-70.00014034695016, 46.69317088478567],
				[-69.23708614772835, 47.44777598732787],
				[-68.90478084987546, 47.184794623394396],
				[-68.23430497910454, 47.35462921812177],
				[-67.79035274928509, 47.066248887716995],
				[-67.79141211614706, 45.702585354182816],
				[-67.13734351262877, 45.137451890638886]
			]
		]
	}
} as Feature)

const librariesSourceTiles = ["https://api.librarydata.uk/libraries/{z}/{x}/{y}.mvt"]
const librariesLayerCirclesPaint = {
	"circle-radius": 5,
	"circle-color": "#1b5e20"
} as CircleLayerSpecification["paint"]

const controlPosition = ref(Position.TOP_LEFT)
const markerCoordinates = ref<LngLatLike>([13.377507, 52.516267])
const map = useMap()

const layout = {
	"line-join": "round",
	"line-cap": "round"
} as LineLayerSpecification["layout"]
const paint = {
	"line-color": "#FF0000",
	"line-width": 8
} as LineLayerSpecification["paint"]

const center = ref<LngLatLike>([10.288107, 49.405078])
const zoom = ref(3)
</script>

<style lang="scss">
@import "maplibre-gl/dist/maplibre-gl.css";
@import "vue-maplibre-gl/src/lib/css/maplibre.scss";

.maplibregl-ctrl .maplibregl-ctrl-icon svg {
	margin: 0 auto;
	path {
		fill: #333333;
	}
}
.maplibregl-style-list {
	color: #333333;
}
</style>
