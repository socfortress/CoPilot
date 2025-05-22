<template>
	<n-popover v-model:show="show" trigger="manual" to="body" content-class="px-0" @clickoutside="closePopup()">
		<template #trigger>
			<slot :loading :toggle-popup />
		</template>

		<div class="flex flex-col gap-4 py-1">
			<div>
				Are you sure you want to delete the Query
				<strong>#{{ query.id }}</strong>
				?
			</div>

			<div class="flex justify-between gap-2">
				<n-button quaternary size="small" @click="closePopup()">Close</n-button>
				<n-button :loading type="error" size="small" @click="deleteQuery()">
					<template #icon>
						<Icon :name="TrashIcon" />
					</template>
					Delete Query
				</n-button>
			</div>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import type { SigmaQuery } from "@/types/sigma.d"
import { NButton, NPopover, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	query: SigmaQuery
}>()

const emit = defineEmits<{
	(e: "deleted", value: SigmaQuery): void
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
