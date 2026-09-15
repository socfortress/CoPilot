import type { DialogApiInjection } from "naive-ui/es/dialog/src/DialogProvider"
import type { MessageApiInjection } from "naive-ui/es/message/src/MessageProvider"
import type { ApiError } from "@/types/common"
import type { CustomerIntegration } from "@/types/integrations"
import { h } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

/**
 * Integrations a customer may configure more than once, each configuration labelled by
 * `instance_name`. Mirrors `MULTI_INSTANCE_INTEGRATIONS` in `app/integrations/routes.py` — the
 * backend is what enforces it; this list only decides whether the UI offers to add another one.
 */
export const MULTI_INSTANCE_INTEGRATIONS = ["Office365"]

export function isMultiInstanceIntegration(integrationName: string): boolean {
	return MULTI_INSTANCE_INTEGRATIONS.includes(integrationName)
}

/** Label for an instance in lists and dialogs; the unnamed instance reads as "Default". */
export function integrationInstanceLabel(integration: CustomerIntegration): string {
	return integration.instance_name || "Default"
}

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
		// Built from render helpers rather than innerHTML: `instance_name` is free text somebody
		// typed into the add-integration form, and interpolating it into markup would execute
		// whatever they stored. Text children are escaped by Vue.
		content: () =>
			h("div", [
				"Are you sure you want to delete the integration: ",
				h("strong", integration.integration_service_name),
				...(integration.instance_name ? [" — ", h("strong", integration.instance_name)] : []),
				" ?"
			]),
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
		.deleteIntegration(integration.customer_code, integration.integration_service_name, integration.instance_name)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Customer integration successfully deleted.")

				// Manual follow-up steps and any resource the cleanup could not remove
				if (res.data?.additional_info) {
					message.info(res.data.additional_info, { duration: 0, closable: true })
				}

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
				message.error(getApiErrorMessage(err as ApiError) || "Agent Delete returned Unauthorized.")
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
