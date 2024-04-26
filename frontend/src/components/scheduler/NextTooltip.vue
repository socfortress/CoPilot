<template>
	<n-tooltip @update:show="getNextRun()" placement="top-end">
		<template #trigger>
			<Icon :name="NextIcon"></Icon>
		</template>
		<template #header>Next run time:</template>
		<div>
			<n-spin :size="12" v-if="loadingNext" />
			<span v-if="!loadingNext">
				{{ nextRunTime ? formatDate(nextRunTime, dFormats.datetimesec) : "-" }}
			</span>
		</div>
	</n-tooltip>
</template>

<script setup lang="ts">
import { ref, toRefs } from "vue"
import { NTooltip, NSpin, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { formatDate } from "@/utils"
import Api from "@/api"
import { useSettingsStore } from "@/stores/settings"

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
