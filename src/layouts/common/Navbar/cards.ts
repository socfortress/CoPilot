import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

const CardsIcon = "fluent:preview-link-20-regular"

export default {
	label: "Cards",
	key: "Cards",
	icon: renderIcon(CardsIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Cards-Basic"
						}
					},
					{ default: () => "Basic" }
				),
			key: "Cards-Basic"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Cards-Ecommerce"
						}
					},
					{ default: () => "Ecommerce" }
				),
			key: "Cards-Ecommerce"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Cards-List"
						}
					},
					{ default: () => "List" }
				),
			key: "Cards-List"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Cards-Extra"
						}
					},
					{ default: () => "Extra" }
				),
			key: "Cards-Extra"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Cards-Combo"
						}
					},
					{ default: () => "Combo" }
				),
			key: "Cards-Combo"
		}
	]
}
