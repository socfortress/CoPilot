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
export const MULTI_INSTANCE_INTEGRATIONS = ["Office365", "AWS"]

export function isMultiInstanceIntegration(integrationName: string): boolean {
	return MULTI_INSTANCE_INTEGRATIONS.includes(integrationName)
}

/** Placeholder for the instance-name field: what an instance *is* differs per integration. */
const INSTANCE_NAME_PLACEHOLDERS: Record<string, string> = {
	Office365: "e.g. company.onmicrosoft.com",
	AWS: "e.g. production (one instance per AWS account and bucket)"
}

export function instanceNamePlaceholder(integrationName: string): string {
	return INSTANCE_NAME_PLACEHOLDERS[integrationName] ?? "e.g. production"
}

/**
 * Auth keys an integration accepts empty. Every other key is required, as before. Mirrors what the
 * backend's provisioning schema treats as optional (`app/integrations/aws/schema/provision.py`).
 */
const OPTIONAL_AUTH_KEYS: Record<string, string[]> = {
	AWS: ["AWS_ACCOUNT_ALIAS", "AWS_ORGANIZATION_ID", "ONLY_LOGS_AFTER"]
}

export function isOptionalAuthKey(integrationName: string, authKeyName: string): boolean {
	return OPTIONAL_AUTH_KEYS[integrationName]?.includes(authKeyName) ?? false
}

/**
 * Auth keys the API never returns: it sends `REDACTED_AUTH_VALUE` instead, and an update that sends
 * that placeholder (or nothing) back keeps the stored value. Mirrors `REDACTED_AUTH_KEYS` in
 * `app/integrations/schema.py`.
 */
export const WRITE_ONLY_AUTH_KEYS = ["SECRET_ACCESS_KEY"]
export const REDACTED_AUTH_VALUE = "********"

export function isWriteOnlyAuthKey(authKeyName: string): boolean {
	return WRITE_ONLY_AUTH_KEYS.includes(authKeyName)
}

/** Placeholders that explain a key's format where its name alone does not. */
const AUTH_KEY_HINTS: Record<string, Record<string, string>> = {
	AWS: {
		ACCESS_KEY_ID: "AKIA…",
		AWS_ACCOUNT_ID: "12-digit account ID",
		AWS_ACCOUNT_ALIAS: "Optional label for the account",
		AWS_ORGANIZATION_ID: "Optional, CloudTrail organization trails only (o-…)",
		BUCKET_NAME: "S3 bucket the logs are exported to",
		SERVICES: "cloudtrail,guardduty:guardduty (service or service:s3-prefix)",
		ONLY_LOGS_AFTER: "Optional, YYYY-MMM-DD (e.g. 2026-OCT-08); defaults to today"
	}
}

export function authKeyPlaceholder(integrationName: string, authKeyName: string): string {
	return AUTH_KEY_HINTS[integrationName]?.[authKeyName] ?? `Input ${authKeyName}...`
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
