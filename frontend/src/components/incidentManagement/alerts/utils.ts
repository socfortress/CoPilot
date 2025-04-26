import type { Alert } from "@/types/incidentManagement/alerts.d"
import type { DialogApiInjection } from "naive-ui/es/dialog/src/DialogProvider"
import type { MessageApiInjection } from "naive-ui/es/message/src/MessageProvider"
import Api from "@/api"
import { h } from "vue"

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
				message.error(err.response?.data?.message || "Alert Delete returned Unauthorized.")
			} else {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
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
