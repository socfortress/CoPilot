<template>
	<n-popover v-model:show="show" trigger="manual" to="body" content-class="px-0" @clickoutside="closePopup()">
		<template #trigger>
			<slot :loading :toggle-popup />
		</template>

		<div class="py-1 flex flex-col gap-2 max-w-80 min-w-72">
			<div>Choose the level to load:</div>

			<n-checkbox-group v-model:value="ruleLevels" class="flex gap-4" :disabled="loading">
				<n-checkbox value="high" label="High" />
				<n-checkbox value="critical" label="Critical" />
			</n-checkbox-group>

			<p class="text-right">
				* It may take several minutes
			</p>

			<div class="flex gap-2 justify-between">
				<n-button quaternary size="small" @click="closePopup()">
					Close
				</n-button>
				<n-button :disabled="!isValid" :loading type="primary" size="small" @click="uploadQueries()">
					Upload
				</n-button>
			</div>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import type { SigmaRuleLevels } from "@/types/sigma.d"
import Api from "@/api"
import { NButton, NCheckbox, NCheckboxGroup, NPopover, useMessage } from "naive-ui"
import { computed, ref } from "vue"

const emit = defineEmits<{
	(e: "updated"): void
}>()

const loading = defineModel<boolean | undefined>("loading", { default: false })

const show = ref(false)
const lastShow = ref(new Date().getTime())
const message = useMessage()
const ruleLevels = ref<SigmaRuleLevels[]>([])
const isValid = computed(() => !!ruleLevels.value.length)

function togglePopup() {
	if (new Date().getTime() - lastShow.value > 500) {
		show.value = !show.value
	}
}

function closePopup() {
	lastShow.value = new Date().getTime()
	show.value = false
}

function uploadQueries() {
	loading.value = true

	Api.sigma
		.uploadRules(ruleLevels.value)
		.then(res => {
			if (res.data.success) {
				emit("updated")
				message.success(res.data?.message || "Successfully uploaded the Sigma queries to the database")
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
