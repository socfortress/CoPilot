import { ref } from "vue"

const healthcheckFilters = ref<Partial<{ time: number; unit: "minutes" | "hours" | "days" }>>({
	time: 1,
	unit: "days"
})

export function useCustomerHealthcheckFilters() {
	return {
		healthcheckFilters
	}
}
