import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

import MapIcon from "@vicons/carbon/Map"

export default {
	label: "Maps",
	key: "maps",
	icon: renderIcon(MapIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "maps-google-maps"
						}
					},
					{ default: () => "Google Maps" }
				),
			key: "maps-google-maps"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "maps-maplibre"
						}
					},
					{ default: () => "MapLibre" }
				),
			key: "maps-maplibre"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "maps-leaflet"
						}
					},
					{ default: () => "Leaflet" }
				),
			key: "maps-leaflet"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "maps-vectormap"
						}
					},
					{ default: () => "Vector Map" }
				),
			key: "maps-vectormap"
		}
	]
}
