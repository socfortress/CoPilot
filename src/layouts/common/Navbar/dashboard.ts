import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

const DashboardIcon = "carbon:dashboard"

export default {
	label: "Dashboard",
	key: "Dashboard",
	icon: renderIcon(DashboardIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Dashboard-Analytics"
						}
					},
					{ default: () => "Analytics" }
				),
			key: "Dashboard-Analytics"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Dashboard-eCommerce"
						}
					},
					{ default: () => "eCommerce" }
				),
			key: "Dashboard-eCommerce"
		}
	]
}
