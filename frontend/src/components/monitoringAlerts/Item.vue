<template>
	<CardEntity :loading :loading-description="loadingDelete ? 'Deleting' : 'Invoking'" :embedded class="min-h-24">
		<template #header>#{{ alert.id }}</template>
		<template #default>
			{{ alert.alert_id }}
		</template>
		<template #mainExtra>
			<div class="flex flex-wrap items-center gap-3">
				<Badge type="active" class="cursor-pointer" @click.stop="gotoIndex(alert.alert_index)">
					<template #iconRight>
						<Icon :name="LinkIcon" :size="14"></Icon>
					</template>
					<template #label>Index / {{ alert.alert_index }}</template>
				</Badge>

				<Badge type="active" class="cursor-pointer" @click.stop="gotoCustomer({ code: alert.customer_code })">
					<template #iconRight>
						<Icon :name="LinkIcon" :size="14"></Icon>
					</template>
					<template #label>Customer #{{ alert.customer_code }}</template>
				</Badge>

				<Badge type="splitted" color="primary">
					<template #label>Source</template>
					<template #value>
						{{ alert.alert_source }}
					</template>
				</Badge>
			</div>
		</template>
		<template #footerExtra>
			<AlertActions
				class="flex flex-wrap gap-3"
				:alert="alert"
				size="small"
				@deleted="emit('deleted')"
				@invoked="emit('invoked')"
				@start-deleting="loadingDelete = true"
				@stop-deleting="loadingDelete = false"
				@start-invoking="loadingInvoke = true"
				@stop-invoking="loadingInvoke = false"
			/>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { MonitoringAlert } from "@/types/monitoringAlerts.d"
import { computed, ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import AlertActions from "./ItemActions.vue"

const { alert, embedded } = defineProps<{
	alert: MonitoringAlert
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "invoked"): void
}>()

const LinkIcon = "carbon:launch"

const { gotoCustomer, gotoIndex } = useGoto()
const loadingDelete = ref(false)
const loadingInvoke = ref(false)
const loading = computed(() => loadingDelete.value || loadingInvoke.value)
</script>
