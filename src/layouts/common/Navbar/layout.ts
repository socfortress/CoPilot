import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

import LayoutIcon from "@vicons/fluent/DualScreenVerticalScroll24Regular"

export default {
	label: "Layout",
	key: "layout",
	icon: renderIcon(LayoutIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "layout-full-width"
						}
					},
					{ default: () => "Full Width" }
				),
			key: "layout-full-width"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "layout-left-sidebar"
						}
					},
					{ default: () => "Left Sidebar" }
				),
			key: "layout-left-sidebar"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "layout-right-sidebar"
						}
					},
					{ default: () => "Right Sidebar" }
				),
			key: "layout-right-sidebar"
		}
	]
}
