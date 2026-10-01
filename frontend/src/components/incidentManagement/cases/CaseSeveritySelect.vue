<template>
	<n-popselect
		:value="caseData.severity ?? FOLLOW"
		:options
		:disabled="loading"
		size="medium"
		to="body"
		@update:value="update"
	>
		<slot :loading />
	</n-popselect>
</template>

<script setup lang="ts">
// A case's severity drives its SLA targets (#1187). "Follow linked alerts" stores
// nothing, so the case takes the most severe of its alerts — and moves with them.
// Admin/analyst only, like escalation: the backend refuses anyone else.
import type { Case, CaseSeverity } from "@/types/incidentManagement/cases"
import { NPopselect, useMessage } from "naive-ui"
import { shallowRef } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

const { caseData } = defineProps<{ caseData: Case }>()
const emit = defineEmits<{ (e: "updated", value: Case): void }>()

const FOLLOW = "__follow__"
const SEVERITIES: CaseSeverity[] = ["Critical", "High", "Medium", "Low", "Informational"]

const message = useMessage()
const loading = shallowRef(false)

const options = [
	{ label: "Follow linked alerts", value: FOLLOW },
	...SEVERITIES.map(severity => ({ label: severity, value: severity }))
]

async function update(value: string) {
	const severity = value === FOLLOW ? null : (value as CaseSeverity)
	if (severity === (caseData.severity ?? null)) return
	loading.value = true
	try {
		await Api.incidentManagement.cases.updateCaseSeverity(caseData.id, severity)
		emit("updated", { ...caseData, severity })
		message.success(severity ? `Severity set to ${severity}` : "Severity follows the linked alerts")
	} catch (err) {
		message.error(getApiErrorMessage(err as never) || "Could not change the severity")
	} finally {
		loading.value = false
	}
}
</script>
