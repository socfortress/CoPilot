import type { CustomerIntegration } from "@/types/integrations.d"
import type { DialogApiInjection } from "naive-ui/es/dialog/src/DialogProvider"
import type { MessageApiInjection } from "naive-ui/es/message/src/MessageProvider"
import Api from "@/api"
import { h } from "vue"

export interface DeleteIntegrationParams {
	integration: CustomerIntegration
	cbBefore?: () => void
	cbSuccess?: () => void
	cbAfter?: () => void
	cbError?: () => void
	message: MessageApiInjection
	dialog: DialogApiInjection
}

export function handleDeleteIntegration({
	integration,
	cbBefore,
	cbSuccess,
	cbAfter,
	cbError,
	dialog,
	message
}: DeleteIntegrationParams) {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the integration: <strong>${integration.integration_service_name}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteIntegration({ integration, cbBefore, cbSuccess, cbAfter, cbError, dialog, message })
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

export function deleteIntegration({
	integration,
	cbBefore,
	cbSuccess,
	cbAfter,
	cbError,
	message
}: DeleteIntegrationParams) {
	if (cbBefore && typeof cbBefore === "function") {
		cbBefore()
	}

	Api.integrations
		.deleteIntegration(integration.customer_code, integration.integration_service_name)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Customer integration successfully deleted.")

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
				message.error(err.response?.data?.message || "Agent Delete returned Unauthorized.")
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
