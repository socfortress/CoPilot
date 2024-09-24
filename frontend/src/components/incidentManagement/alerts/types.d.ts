import type { AlertsFilterTypes, AlertsListFilterValue } from "@/api/endpoints/incidentManagement"

export interface AlertsListFilter {
	type: AlertsFilterTypes
	value: AlertsListFilterValue
}
