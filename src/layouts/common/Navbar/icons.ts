import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

import IconsIcon from "@vicons/fluent/Icons24Regular"

export default {
	label: "Icons",
	key: "icons",
	icon: renderIcon(IconsIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "icons-xicons"
						}
					},
					{ default: () => "xIcons" }
				),
			key: "icons-xicons"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "icons-flag"
						}
					},
					{ default: () => "Flag" }
				),
			key: "icons-flag"
		}
	]
}
