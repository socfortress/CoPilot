<template>
	<n-popover v-model:show="show" trigger="manual" to="body" content-class="px-0" @clickoutside="closePopup()">
		<template #trigger>
			<slot :loading :toggle-popup />
		</template>

		<div class="flex min-w-52 flex-col justify-center gap-4 py-1">
			<div class="flex items-center justify-center gap-2 py-3">
				<span>Active</span>
				<n-switch v-model:value="model.active" :disabled="loading" />
			</div>

			<div class="flex justify-between gap-2">
				<n-button quaternary size="small" @click="closePopup()">Close</n-button>
				<n-button :disabled="!dirty" :loading type="primary" size="small" @click="updateActive()">
					Save
				</n-button>
			</div>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import type { SigmaQuery } from "@/types/sigma.d"
import { NButton, NPopover, NSwitch, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"

const props = defineProps<{
	query: SigmaQuery
}>()

const emit = defineEmits<{
	(e: "updated", value: SigmaQuery): void
}>()

const { query } = toRefs(props)

const loading = defineModel<boolean | undefined>("loading", { default: false })

const show = ref(false)
const lastShow = ref(new Date().getTime())
const message = useMessage()
const model = ref<{ active: boolean }>({ active: false })
const active = ref<boolean>(false)
const dirty = computed(() => active.value !== model.value.active)

watch(show, val => {
	if (val && !loading.value) {
		setModel()
	}
})

function togglePopup() {
	if (new Date().getTime() - lastShow.value > 500) {
		show.value = !show.value
	}
}

function closePopup() {
	lastShow.value = new Date().getTime()
	show.value = false
}

function setModel() {
	active.value = !!query.value.active
	model.value.active = active.value
}

function updateActive() {
	if (query.value.rule_name) {
		loading.value = true

		Api.sigma
			.setQueryActive(query.value.rule_name, model.value.active)
			.then(res => {
				if (res.data.success) {
					emit("updated", res.data.sigma_queries[0])
					message.success(res.data?.message || "Sigma query updated successfully")
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

onBeforeMount(() => {
	setModel()
})
</script>
