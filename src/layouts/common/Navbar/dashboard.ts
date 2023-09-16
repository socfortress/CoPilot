import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

import DashboardIcon from "@vicons/carbon/Dashboard"

export default {
	label: "Dashboard",
	key: "dashboard",
	icon: renderIcon(DashboardIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "analytics"
						}
					},
					{ default: () => "Analytics" }
				),
			key: "analytics"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "ecommerce"
						}
					},
					{ default: () => "eCommerce" }
				),
			key: "ecommerce"
		}
	]
}
