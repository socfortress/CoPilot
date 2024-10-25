<template>
	<n-tooltip placement="top-end" @update:show="getNextRun()">
		<template #trigger>
			<Icon :name="NextIcon"></Icon>
		</template>
		<template #header>Next run time:</template>
		<div>
			<n-spin v-if="loadingNext" :size="12" />
			<span v-if="!loadingNext">
				{{ nextRunTime ? formatDate(nextRunTime, dFormats.datetimesec) : "-" }}
			</span>
		</div>
	</n-tooltip>
</template>

<script setup lang="ts">
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NSpin, NTooltip, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"

const props = defineProps<{ jobId: string }>()
const { jobId } = toRefs(props)

const NextIcon = "carbon:view-next"

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loadingNext = ref(false)
const nextRunTime = ref<Date | null>(null)

function getNextRun() {
	if (nextRunTime.value) {
		return
	}
	loadingNext.value = true

	Api.scheduler
		.getNextRun(jobId.value)
		.then(res => {
			if (res.data.success) {
				nextRunTime.value = res.data.next_run_time
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingNext.value = false
		})
}
</script>
