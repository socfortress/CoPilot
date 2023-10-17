import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

const ChartIcon = "carbon:chart-histogram"

export default {
	label: "Charts",
	key: "Charts",
	icon: renderIcon(ChartIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Charts-ApexCharts"
						}
					},
					{ default: () => "ApexCharts" }
				),
			key: "Charts-ApexCharts"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Charts-ChartJS"
						}
					},
					{ default: () => "ChartJS" }
				),
			key: "Charts-ChartJS"
		}
	]
}
