<template>
	<n-popover trigger="manual" to="body" content-class="px-0" v-model:show="show" @clickoutside="closePopup()">
		<template #trigger>
			<slot :loading :togglePopup />
		</template>

		<div class="py-1 flex flex-col gap-4 max-w-80">
			<div>This will download ALL Sigma queries, are you sure you want to proceed?</div>

			<div class="flex gap-2 justify-between">
				<n-button @click="closePopup()" quaternary size="small">Close</n-button>
				<n-button :loading @click="downloadQueries()" type="primary" size="small">Yes I'm sure</n-button>
			</div>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { NButton, NPopover, useMessage } from "naive-ui"
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
