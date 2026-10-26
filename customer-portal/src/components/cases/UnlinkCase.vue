<template>
	<n-popconfirm to="body" @positive-click="() => void unlinkCase()">
		<template #trigger>
			<n-button :size :focusable="false" :loading="unlinking">
				<template #icon>
					<Icon name="carbon:unlink" />
				</template>
				{{ label || $t("cases.unlinkCase.label") }}
			</n-button>
		</template>
		{{ $t("cases.unlinkCase.confirm") }}
	</n-popconfirm>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { ApiError } from "@/types/common"
import { NButton, NPopconfirm, useMessage } from "naive-ui"
import { ref } from "vue"
import { useI18n } from "vue-i18n"
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
const { t } = useI18n()

async function unlinkCase() {
	unlinking.value = true

	try {
		const res = await Api.cases.unlinkCaseFromAlert(props.caseId, props.alertId)
		if (res.data.success) {
			emit("unlinked", props.caseId)
			message.success(res.data?.message || t("cases.unlinkCase.unlinked"))
		} else {
			message.warning(res.data?.message || t("cases.unlinkCase.failed"))
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || t("cases.unlinkCase.failed"))
	} finally {
		unlinking.value = false
	}
}
</script>
