import dayjs from "dayjs"
import Api from "@/api"
import { ElMessage, ElMessageBox } from "element-plus"
import { Agent } from "@/types/agents"

export function isAgentOnline(last_seen: string) {
    const lastSeenDate = dayjs(last_seen)
    if (!lastSeenDate.isValid()) return false

    return lastSeenDate.isAfter(dayjs().subtract(1, "h"))
}

export interface ToggleAgentCriticalParams {
    agentId: string
    criticalStatus: boolean
    cbBefore?: () => void
    cbSuccess?: () => void
    cbAfter?: () => void
    cbError?: () => void
}

export function toggleAgentCritical({ agentId, criticalStatus, cbBefore, cbSuccess, cbAfter, cbError }: ToggleAgentCriticalParams) {
    if (cbBefore && typeof cbBefore === "function") {
        cbBefore()
    }
    const method = criticalStatus ? "markNonCritical" : "markCritical"

    Api.agents[method](agentId)
        .then(res => {
            if (res.data.success) {
                ElMessage({
                    message: "Agent Criticality Updated Successfully",
                    type: "success"
                })

                if (cbSuccess && typeof cbSuccess === "function") {
                    cbSuccess()
                }
            } else {
                ElMessage({
                    message: res.data?.message || "Failed to Update Agent Criticality.",
                    type: "error"
                })

                if (cbError && typeof cbError === "function") {
                    cbError()
                }
            }
        })
        .catch(err => {
            if (err.response.status === 401) {
                ElMessage({
                    message: err.response?.data?.message || "Agent Criticality Update returned Unauthorized.",
                    type: "error"
                })
            } else {
                ElMessage({
                    message: err.response?.data?.message || "Failed to Update Agent Criticality",
                    type: "error"
                })
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
}

export function handleDeleteAgent({ agent, cbBefore, cbSuccess, cbAfter, cbError }: DeleteAgentParams) {
    ElMessageBox.confirm(`Are you sure you want to delete the agent:<br/><strong>${agent.hostname}</strong> ?`, "Warning", {
        confirmButtonText: "Yes I'm sure",
        confirmButtonClass: "el-button--warning",
        cancelButtonText: "Cancel",
        type: "warning",
        dangerouslyUseHTMLString: true,
        customStyle: {
            width: "90%",
            maxWidth: "400px"
        }
    })
        .then(() => {
            deleteAgent({ agent, cbBefore, cbSuccess, cbAfter, cbError })
        })
        .catch(() => {
            ElMessage({
                type: "info",
                message: "Delete canceled"
            })
        })
}

export function deleteAgent({ agent, cbBefore, cbSuccess, cbAfter, cbError }: DeleteAgentParams) {
    if (cbBefore && typeof cbBefore === "function") {
        cbBefore()
    }

    Api.agents
        .deleteAgent(agent.agent_id)
        .then(res => {
            if (res.data.success) {
                ElMessage({
                    message: "Agent was successfully deleted.",
                    type: "success"
                })

                if (cbSuccess && typeof cbSuccess === "function") {
                    cbSuccess()
                }
            } else {
                ElMessage({
                    message: res.data?.message || "An error occurred. Please try again later.",
                    type: "error"
                })

                if (cbError && typeof cbError === "function") {
                    cbError()
                }
            }
        })
        .catch(err => {
            if (err.response.status === 401) {
                ElMessage({
                    message: err.response?.data?.message || "Agent Delete returned Unauthorized.",
                    type: "error"
                })
            } else {
                ElMessage({
                    message: err.response?.data?.message || "An error occurred. Please try again later.",
                    type: "error"
                })
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
