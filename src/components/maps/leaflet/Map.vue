<template>
	<l-map ref="map" v-model:zoom="zoom" :center="[47.41322, -1.219482]" :useGlobalLeaflet="false">
		<!--
						<l-tile-layer
						url="http://tile.stamen.com/watercolor/{z}/{x}/{y}.jpg"
						layer-type="base"
						name="Stamen Watercolor"
						attribution="Map tiles by <a href='http://stamen.com'>Stamen Design</a>, under <a href='http://creativecommons.org/licenses/by/3.0'>CC BY 3.0</a>. Data by <a href='http://openstreetmap.org'>OpenStreetMap</a>, under <a href='http://creativecommons.org/licenses/by-sa/3.0'>CC BY SA</a>."
						/>
					-->
		<l-tile-layer
			url="https://stamen-tiles.a.ssl.fastly.net/toner/{z}/{x}/{y}.png"
			layer-type="base"
			name="Stamen Toner"
			attribution="Map tiles by <a href='http://stamen.com'>Stamen Design</a>, under <a href='http://creativecommons.org/licenses/by/3.0'>CC BY 3.0</a>. Data by <a href='http://openstreetmap.org'>OpenStreetMap</a>, under <a href='http://creativecommons.org/licenses/by-sa/3.0'>CC BY SA</a>."
		></l-tile-layer>
		<l-tile-layer
			url="https://stamen-tiles.a.ssl.fastly.net/terrain/{z}/{x}/{y}.png"
			layer-type="base"
			name="Stamen Terrain"
			attribution="Map tiles by <a href='http://stamen.com'>Stamen Design</a>, under <a href='http://creativecommons.org/licenses/by/3.0'>CC BY 3.0</a>. Data by <a href='http://openstreetmap.org'>OpenStreetMap</a>, under <a href='http://creativecommons.org/licenses/by-sa/3.0'>CC BY SA</a>."
		></l-tile-layer>
		<l-tile-layer
			url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
			layer-type="base"
			name="OpenTopoMap"
			attribution="Map data: &copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors, <a href='http://viewfinderpanoramas.org'>SRTM</a> | Map style: &copy; <a href='https://opentopomap.org'>OpenTopoMap</a> (<a href='https://creativecommons.org/licenses/by-sa/3.0/'>CC-BY-SA</a>)"
		></l-tile-layer>
		<l-tile-layer
			url="https://map1.vis.earthdata.nasa.gov/wmts-webmerc/VIIRS_CityLights_2012/default//GoogleMapsCompatible_Level{maxZoom}/{z}/{y}/{x}.jpg"
			layer-type="base"
			name="NASA/GSFC/Earth"
			attribution="Imagery provided by services from the Global Imagery Browse Services (GIBS), operated by the NASA/GSFC/Earth Science Data and Information System (<a href='https://earthdata.nasa.gov'>ESDIS</a>) with funding provided by NASA/HQ."
			:bounds="[
				[-85.0511287776, -179.999999975],
				[85.0511287776, 179.999999975]
			]"
			:minZoom="1"
			:maxZoom="8"
		></l-tile-layer>
		<l-tile-layer
			url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png"
			layer-type="base"
			name="Positron"
			attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>"
		></l-tile-layer>
		<l-tile-layer
			url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png"
			layer-type="base"
			name="Dark Matter"
			attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>"
		></l-tile-layer>
		<l-tile-layer
			url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
			layer-type="base"
			name="OpenStreetMap"
			attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors"
		></l-tile-layer>

		<l-control-layers />
		<l-marker :lat-lng="[47.85549887088562, 10.087190790477521]" draggable>
			<l-tooltip>tooltip</l-tooltip>
		</l-marker>

		<l-marker :lat-lng="[45.39799982105989, 9.05183645038641]">
			<l-icon :icon-url="logo" :icon-size="iconSize" />
		</l-marker>

		<l-marker :lat-lng="[46.731739550358135, -1.3987144591730958]" draggable>
			<l-popup>popup</l-popup>
		</l-marker>

		<l-polyline
			:lat-lngs="[
				[47.334852, -1.509485],
				[47.342596, -1.328731],
				[47.241487, -1.190568],
				[47.234787, -1.358337]
			]"
			color="green"
		></l-polyline>
		<l-polygon
			:lat-lngs="[
				[46.334852, -1.509485],
				[46.342596, -1.328731],
				[46.241487, -1.190568],
				[46.234787, -1.358337]
			]"
			color="#41b782"
			:fill="true"
			:fillOpacity="0.5"
			fillColor="#41b782"
		/>
		<l-rectangle
			:lat-lngs="[
				[46.334852, -1.509485],
				[46.342596, -1.328731],
				[46.241487, -1.190568],
				[46.234787, -1.358337]
			]"
			:fill="true"
			color="#35495d"
		/>
		<l-rectangle
			:bounds="[
				[46.334852, -1.190568],
				[46.241487, -1.090357]
			]"
		>
			<l-popup>lol</l-popup>
		</l-rectangle>
	</l-map>
</template>
<script setup lang="ts">
import logo from "@/assets/images/brand-logo_light.svg?url"

import { ref } from "vue"

import "leaflet/dist/leaflet.css"
import {
	LMap,
	LIcon,
	LTileLayer,
	LMarker,
	LControlLayers,
	LTooltip,
	LPopup,
	LPolyline,
	LPolygon,
	LRectangle
} from "@vue-leaflet/vue-leaflet"

const zoom = ref(4)
const iconSize = ref([50, 50])
</script>
