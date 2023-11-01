import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

const LayoutIcon = "fluent:dual-screen-vertical-scroll-24-regular"

export default {
	label: "Layout",
	key: "Layout",
	icon: renderIcon(LayoutIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Layout-FullWidth"
						}
					},
					{ default: () => "Full Width" }
				),
			key: "Layout-FullWidth"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Layout-LeftSidebar"
						}
					},
					{ default: () => "Left Sidebar" }
				),
			key: "Layout-LeftSidebar"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Layout-RightSidebar"
						}
					},
					{ default: () => "Right Sidebar" }
				),
			key: "Layout-RightSidebar"
		}
	]
}
