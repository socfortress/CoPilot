<template>
	<n-popconfirm to="body" @positive-click="unlinkCase">
		<template #trigger>
			<n-button :size :focusable="false" :loading="unlinking">
				<template #icon>
					<Icon name="carbon:unlink" />
				</template>
				{{ label || "Unlink Case" }}
			</n-button>
		</template>
		Are you sure you want to unlink this case from the alert?
	</n-popconfirm>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { ApiError } from "@/types/common"
import { NButton, NPopconfirm, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	alertId: number
	caseId: number
	size?: ButtonSize
	label?: string
}>()

const emit = defineEmits<{
	(e: "unlinked", value: number): void
}>()

const unlinking = ref(false)
const message = useMessage()

function unlinkCase() {
	unlinking.value = true

	Api.cases
		.unlinkCaseFromAlert(props.caseId, props.alertId)
		.then(res => {
			if (res.data.success) {
				emit("unlinked", props.caseId)
				message.success(res.data?.message || "Case unlinked from alert successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			unlinking.value = false
		})
}
</script>
