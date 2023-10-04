import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

import ToolboxIcon from "@vicons/carbon/ToolBox"

export default {
	label: "Toolbox",
	key: "Toolbox",
	icon: renderIcon(ToolboxIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "toolbox-refresh-tool"
						}
					},
					{
						default: () => "Refresh Tool"
					}
				),
			key: "toolbox-refresh-tool"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "toolbox-tour"
						}
					},
					{
						default: () => "Tour"
					}
				),
			key: "toolbox-tour"
		}
	]
}
