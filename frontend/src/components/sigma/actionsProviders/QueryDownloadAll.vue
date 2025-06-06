<template>
	<n-popover v-model:show="show" trigger="manual" to="body" content-class="px-0" @clickoutside="closePopup()">
		<template #trigger>
			<slot :loading :toggle-popup />
		</template>

		<div class="flex max-w-80 flex-col gap-4 py-1">
			<div>This will download ALL Sigma queries, are you sure you want to proceed?</div>

			<div class="flex justify-between gap-2">
				<n-button quaternary size="small" @click="closePopup()">Close</n-button>
				<n-button :loading type="primary" size="small" @click="downloadQueries()">Yes I'm sure</n-button>
			</div>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import { NButton, NPopover, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"

const emit = defineEmits<{
	(e: "updated"): void
}>()

const loading = defineModel<boolean | undefined>("loading", { default: false })

const show = ref(false)
const lastShow = ref(new Date().getTime())
const message = useMessage()

function togglePopup() {
	if (new Date().getTime() - lastShow.value > 500) {
		show.value = !show.value
	}
}

function closePopup() {
	lastShow.value = new Date().getTime()
	show.value = false
}

function downloadQueries() {
	loading.value = true

	Api.sigma
		.downloadRules()
		.then(res => {
			if (res.data.success) {
				emit("updated")
				message.success(res.data?.message || "Sigma queries downloaded successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}
</script>
