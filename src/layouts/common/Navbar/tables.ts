import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

const TablesIcon = "carbon:data-table"

export default {
	label: "Tables",
	key: "Tables",
	icon: renderIcon(TablesIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Tables-Base"
						}
					},
					{ default: () => "Base" }
				),
			key: "Tables-Base"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Tables-DataTable"
						}
					},
					{ default: () => "Data Table" }
				),
			key: "Tables-Data-table"
		}
		/*
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Tables-Grid"
						}
					},
					{ default: () => "Data Grid" }
				),
			key: "Tables-Grid"
		}
		*/
	]
}
