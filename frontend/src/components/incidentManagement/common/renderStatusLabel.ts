import type { SelectOption } from "naive-ui"
import type { VNodeChild } from "vue"
import { NTooltip } from "naive-ui"
import { h } from "vue"
import Icon from "@/components/common/Icon.vue"
import { PENDING_CUSTOMER_HELP } from "./status"

/**
 * `render-label` for status pickers: "Waiting on customer" carries a help icon explaining
 * that it stops the SLA clocks, so nobody parks an item there without knowing it.
 */
export function renderStatusLabel(option: SelectOption): VNodeChild {
	if (option.value !== "PENDING_CUSTOMER") return option.label as string
	return h("span", { class: "flex items-center gap-2" }, [
		h("span", option.label as string),
		h(NTooltip, { placement: "right", style: "max-width: 280px" }, {
			trigger: () => h("span", { class: "flex opacity-60", "data-testid": "pending-customer-help" }, [h(Icon, { name: "carbon:information", size: 14 })]),
			default: () => PENDING_CUSTOMER_HELP
		})
	])
}
