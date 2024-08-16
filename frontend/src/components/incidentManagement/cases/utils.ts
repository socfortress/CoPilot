import { h } from "vue"
import Api from "@/api"
import type { MessageApiInjection } from "naive-ui/es/message/src/MessageProvider"
import type { DialogApiInjection } from "naive-ui/es/dialog/src/DialogProvider"
import type { Case } from "@/types/incidentManagement/cases.d"

export interface DeleteCaseParams {
	caseData: Case
	cbBefore?: () => void
	cbSuccess?: () => void
	cbAfter?: () => void
	cbError?: () => void
	message: MessageApiInjection
	dialog: DialogApiInjection
}

export function handleDeleteCase({
	caseData,
	cbBefore,
	cbSuccess,
	cbAfter,
	cbError,
	dialog,
	message
}: DeleteCaseParams) {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the Case:<br/><strong>${caseData.id} - ${caseData.case_name}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteAlert({ caseData, cbBefore, cbSuccess, cbAfter, cbError, dialog, message })
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

export function deleteAlert({ caseData, cbBefore, cbSuccess, cbAfter, cbError, message }: DeleteCaseParams) {
	if (cbBefore && typeof cbBefore === "function") {
		cbBefore()
	}

	Api.incidentManagement
		.deleteCase(caseData.id)
		.then(res => {
			if (res.data.success) {
				message.success("Case was successfully deleted.")

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
				message.error(err.response?.data?.message || "Case Delete returned Unauthorized.")
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
