<template>
	<n-popover v-for="linkedCase of linkedCases" :key="linkedCase.id" placement="top" to="body" trigger="click">
		<template #trigger>
			<code class="text-primary cursor-pointer">
				#{{ linkedCase.id }}
				<Icon :name="MenuIcon" :size="14" class="relative top-0.5" />
			</code>
		</template>
		<div class="flex flex-col gap-3 px-1 py-2">
			<CaseItem
				:case-data="{ ...linkedCase, alerts: alert ? [alert] : [] }"
				compact
				embedded
				@click="gotoIncidentManagementCases(linkedCase.id)"
			/>
			<div class="flex items-center justify-end gap-3">
				<n-button
					size="small"
					secondary
					type="warning"
					:loading="loadingId === linkedCase.id"
					@click="unlink(linkedCase.id)"
				>
					<template #icon>
						<Icon :name="UnlinkIcon" />
					</template>
					Unlink Case
				</n-button>
			</div>
		</div>
	</n-popover>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts.d"
import { NButton, NPopover, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"

const props = defineProps<{ alert: Alert }>()

const emit = defineEmits<{
	(e: "updated", value: Alert): void
	(e: "unlinked"): void
}>()

const CaseItem = defineAsyncComponent(() => import("../cases/CaseItem.vue"))

const UnlinkIcon = "carbon:unlink"
const MenuIcon = "carbon:overflow-menu-horizontal"
const loadingId = ref<number | false>(false)
const alert = ref<Alert>(props.alert)
const message = useMessage()
const { gotoIncidentManagementCases } = useNavigation()
const linkedCases = computed(() => alert.value?.linked_cases || [])

function updateAlert(updatedAlert: Alert) {
	alert.value = updatedAlert
	emit("updated", updatedAlert)
}

function unlink(caseId: number) {
	if (!alert.value) return

	loadingId.value = caseId

	Api.incidentManagement.cases
		.unlinkCase(alert.value.id, caseId)
		.then(res => {
			if (res.data.success) {
				updateAlert({
					...alert.value,
					linked_cases: alert.value.linked_cases.filter(c => c.id !== caseId)
				})

				emit("unlinked")
				message.success(res.data?.message || "Case unlinked successfully")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingId.value = false
		})
}

watch(
	() => props.alert,
	() => {
		alert.value = props.alert
	},
	{
		immediate: true
	}
)
</script>
