import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

import CardsIcon from "@vicons/fluent/PreviewLink20Regular"

export default {
	label: "Cards",
	key: "cards",
	icon: renderIcon(CardsIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "cards-basic"
						}
					},
					{ default: () => "Basic" }
				),
			key: "cards-basic"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "cards-ecommerce"
						}
					},
					{ default: () => "Ecommerce" }
				),
			key: "cards-ecommerce"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "cards-list"
						}
					},
					{ default: () => "List" }
				),
			key: "cards-list"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "cards-extra"
						}
					},
					{ default: () => "Extra" }
				),
			key: "cards-extra"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "cards-combo"
						}
					},
					{ default: () => "Combo" }
				),
			key: "cards-combo"
		}
	]
}
