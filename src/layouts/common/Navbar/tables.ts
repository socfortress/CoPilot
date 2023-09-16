import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

import TablesIcon from "@vicons/carbon/DataTable"

export default {
	label: "Tables",
	key: "tables",
	icon: renderIcon(TablesIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "tables-base"
						}
					},
					{ default: () => "Base" }
				),
			key: "tables-base"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "tables-data-table"
						}
					},
					{ default: () => "Data Table" }
				),
			key: "tables-data-table"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "tables-grid"
						}
					},
					{ default: () => "Data Grid" }
				),
			key: "tables-grid"
		}
	]
}
