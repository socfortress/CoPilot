import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

const MapIcon = "carbon:map"

export default {
	label: "Maps",
	key: "Maps",
	icon: renderIcon(MapIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Maps-GoogleMaps"
						}
					},
					{ default: () => "Google Maps" }
				),
			key: "Maps-GoogleMaps"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Maps-MapLibre"
						}
					},
					{ default: () => "MapLibre" }
				),
			key: "Maps-MapLibre"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Maps-Leaflet"
						}
					},
					{ default: () => "Leaflet" }
				),
			key: "Maps-Leaflet"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Maps-VectorMap"
						}
					},
					{ default: () => "Vector Map" }
				),
			key: "Maps-VectorMap"
		}
	]
}
