import dayjs from "@/utils/dayjs"
import Api from "@/api"
import { type Agent } from "@/types/agents.d"
import type { MessageApiInjection } from "naive-ui/es/message/src/MessageProvider"
import type { DialogApiInjection } from "naive-ui/es/dialog/src/DialogProvider"
import { h } from "vue"

export function isAgentOnline(lastSeen: string) {
	const lastSeenDate = dayjs(lastSeen)
	if (!lastSeenDate.isValid()) return false
	if (!dayjs().isAfter(lastSeenDate)) return false

	return lastSeenDate.isAfter(dayjs().subtract(1, "h"))
}

export interface ToggleAgentCriticalParams {
	agentId: string
	criticalStatus: boolean
	cbBefore?: () => void
	cbSuccess?: () => void
	cbAfter?: () => void
	cbError?: () => void
	message: MessageApiInjection
}

export function toggleAgentCritical({
	agentId,
	criticalStatus,
	cbBefore,
	cbSuccess,
	cbAfter,
	cbError,
	message
}: ToggleAgentCriticalParams) {
	if (cbBefore && typeof cbBefore === "function") {
		cbBefore()
	}
	const method = criticalStatus ? "markNonCritical" : "markCritical"

	Api.agents[method](agentId)
		.then(res => {
			if (res.data.success) {
				message.success("Agent Criticality Updated Successfully")

				if (cbSuccess && typeof cbSuccess === "function") {
					cbSuccess()
				}
			} else {
				message.error(res.data?.message || "Failed to Update Agent Criticality.")

				if (cbError && typeof cbError === "function") {
					cbError()
				}
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(err.response?.data?.message || "Agent Criticality Update returned Unauthorized.")
			} else {
				message.error(err.response?.data?.message || "Failed to Update Agent Criticality")
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

export interface DeleteAgentParams {
	agent: Agent
	cbBefore?: () => void
	cbSuccess?: () => void
	cbAfter?: () => void
	cbError?: () => void
	message: MessageApiInjection
	dialog: DialogApiInjection
}

export function handleDeleteAgent({
	agent,
	cbBefore,
	cbSuccess,
	cbAfter,
	cbError,
	dialog,
	message
}: DeleteAgentParams) {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the Agent:<br/><strong>${agent.hostname}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteAgent({ agent, cbBefore, cbSuccess, cbAfter, cbError, dialog, message })
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

export function deleteAgent({ agent, cbBefore, cbSuccess, cbAfter, cbError, message }: DeleteAgentParams) {
	if (cbBefore && typeof cbBefore === "function") {
		cbBefore()
	}

	Api.agents
		.deleteAgent(agent.agent_id)
		.then(res => {
			if (res.data.success) {
				message.success("Agent was successfully deleted.")

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
