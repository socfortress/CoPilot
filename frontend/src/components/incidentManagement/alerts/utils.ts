import type { DialogApiInjection } from "naive-ui/es/dialog/src/DialogProvider"
import type { MessageApiInjection } from "naive-ui/es/message/src/MessageProvider"
import type { ApiError } from "@/types/common"
import type { Alert, AlertVerdict, FalsePositiveReason } from "@/types/incidentManagement/alerts"
import { h } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

export interface DeleteAlertParams {
	alert: Alert
	cbBefore?: () => void
	cbSuccess?: () => void
	cbAfter?: () => void
	cbError?: () => void
	message: MessageApiInjection
	dialog: DialogApiInjection
}

export function handleDeleteAlert({
	alert,
	cbBefore,
	cbSuccess,
	cbAfter,
	cbError,
	dialog,
	message
}: DeleteAlertParams) {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the Alert:<br/><strong>${alert.id} - ${alert.alert_name}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteAlert({ alert, cbBefore, cbSuccess, cbAfter, cbError, dialog, message })
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

export function deleteAlert({ alert, cbBefore, cbSuccess, cbAfter, cbError, message }: DeleteAlertParams) {
	if (cbBefore && typeof cbBefore === "function") {
		cbBefore()
	}

	Api.incidentManagement.alerts
		.deleteAlert(alert.id)
		.then(res => {
			if (res.data.success) {
				message.success("Alert was successfully deleted.")

				if (cbSuccess && typeof cbSuccess === "function") {
					cbSuccess()
				}
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")

				if (cbError && typeof cbError === "function") {
					cbError()
				}
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(getApiErrorMessage(err as ApiError) || "Alert Delete returned Unauthorized.")
			} else {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			}

			if (cbError && typeof cbError === "function") {
				cbError()
			}
		})
		.finally(() => {
			if (cbAfter && typeof cbAfter === "function") {
				cbAfter()
			}
		})
}

const FALSE_POSITIVE_REASON_LABELS: Record<FalsePositiveReason, string> = {
	EXPECTED_ACTIVITY: "Expected / legitimate activity",
	KNOWN_APPLICATION: "Known application or service",
	AUTHORIZED_USER: "Authorized user activity",
	RULE_TOO_SENSITIVE: "Detection rule too sensitive",
	OTHER: "Other"
}

/**
 * Human label for a stored false-positive reason. Falls back to the raw value so a reason
 *  added on the backend before the frontend knows about it still renders something.
 */
export function falsePositiveReasonLabel(reason: FalsePositiveReason | string | null): string {
	if (!reason) return ""
	return FALSE_POSITIVE_REASON_LABELS[reason as FalsePositiveReason] ?? reason
}

const VERDICT_LABELS: Record<AlertVerdict, string> = {
	TRUE_POSITIVE: "True positive",
	FALSE_POSITIVE: "False positive"
}

/**
 * Human label for a verdict. `null` is untriaged, which is a real state rather than an
 *  error, so it gets a label of its own instead of an empty string.
 */
export function verdictLabel(verdict: AlertVerdict | null): string {
	if (!verdict) return "Not triaged"
	return VERDICT_LABELS[verdict] ?? verdict
}
