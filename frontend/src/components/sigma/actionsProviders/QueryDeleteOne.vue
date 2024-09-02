<template>
	<n-popover trigger="manual" to="body" content-class="px-0" v-model:show="show" @clickoutside="closePopup()">
		<template #trigger>
			<slot :loading :togglePopup />
		</template>

		<div class="py-1 flex flex-col gap-4">
			<div>
				Are you sure you want to delete the Query
				<strong>#{{ query.id }}</strong>
				?
			</div>

			<div class="flex gap-2 justify-between">
				<n-button @click="closePopup()" quaternary size="small">Close</n-button>
				<n-button :loading @click="deleteQuery()" type="error" size="small">
					<template #icon><Icon :name="TrashIcon" /></template>
					Delete Query
				</n-button>
			</div>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import { ref, toRefs } from "vue"
import { NButton, NPopover, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import type { SigmaQuery } from "@/types/sigma.d"

const emit = defineEmits<{
	(e: "deleted", value: SigmaQuery): void
}>()

const props = defineProps<{
	query: SigmaQuery
}>()
const { query } = toRefs(props)

const loading = defineModel<boolean | undefined>("loading", { default: false })

const TrashIcon = "carbon:trash-can"
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

function deleteQuery() {
	if (query.value.rule_name) {
		loading.value = true

		Api.sigma
			.deleteRule(query.value.rule_name)
			.then(res => {
				if (res.data.success) {
					emit("deleted", query.value)
					message.success(res.data?.message || "Sigma query deleted successfully")
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
}
</script>
