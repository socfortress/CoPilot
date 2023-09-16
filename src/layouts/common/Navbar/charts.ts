import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

import ChartIcon from "@vicons/carbon/ChartHistogram"

export default {
	label: "Charts",
	key: "charts",
	icon: renderIcon(ChartIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "charts-apexcharts"
						}
					},
					{ default: () => "ApexCharts" }
				),
			key: "charts-apexcharts"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "charts-chartjs"
						}
					},
					{ default: () => "ChartJS" }
				),
			key: "charts-chartjs"
		}
	]
}
