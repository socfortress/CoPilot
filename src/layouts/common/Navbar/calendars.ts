import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"

import CalendarIcon from "@vicons/carbon/Calendar"

export default {
	label: "Calendars",
	key: "calendars",
	icon: renderIcon(CalendarIcon),
	children: [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "full-calendar"
						}
					},
					{ default: () => "Full Calendar" }
				),
			key: "full-calendar"
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "vue-cal"
						}
					},
					{ default: () => "Vue Cal" }
				),
			key: "vue-cal"
		}
	]
}
