<template>
	<n-spin :show="loading" :description="loadingDelete ? 'Deleting' : 'Invoking'">
		<div class="monitoring-alerts-item flex flex-col gap-2 px-5 py-3" :class="{ embedded }">
			<div class="header-box flex justify-between">
				<div class="id flex items-center">#{{ alert.id }}</div>
			</div>
			<div class="main-box flex items-center justify-between gap-4">
				<div class="content">
					<div class="title">{{ alert.alert_id }}</div>

					<div class="badges-box flex flex-wrap items-center gap-3 mt-4">
						<Badge type="active" class="cursor-pointer" @click="gotoIndex(alert.alert_index)">
							<template #iconRight>
								<Icon :name="LinkIcon" :size="14"></Icon>
							</template>
							<template #label>Index / {{ alert.alert_index }}</template>
						</Badge>

						<Badge
							type="active"
							class="cursor-pointer"
							@click="gotoCustomer({ code: alert.customer_code })"
						>
							<template #iconRight>
								<Icon :name="LinkIcon" :size="14"></Icon>
							</template>
							<template #label>Customer #{{ alert.customer_code }}</template>
						</Badge>

						<Badge type="splitted">
							<template #label>Source</template>
							<template #value>{{ alert.alert_source }}</template>
						</Badge>
					</div>
				</div>

				<AlertActions
					class="actions-box"
					:alert="alert"
					@deleted="emit('deleted')"
					@invoked="emit('invoked')"
					@startDeleting="loadingDelete = true"
					@stopDeleting="loadingDelete = false"
					@startInvoking="loadingInvoke = true"
					@stopInvoking="loadingInvoke = false"
				/>
			</div>
			<div class="footer-box flex justify-between items-center gap-3">
				<AlertActions
					class="actions-box !flex-row"
					:alert="alert"
					size="small"
					inline
					@deleted="emit('deleted')"
					@invoked="emit('invoked')"
					@startDeleting="loadingDelete = true"
					@stopDeleting="loadingDelete = false"
					@startInvoking="loadingInvoke = true"
					@stopInvoking="loadingInvoke = false"
				/>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, ref } from "vue"
import AlertActions from "./ItemActions.vue"
import { NSpin } from "naive-ui"
import { useGoto } from "@/composables/useGoto"
import type { MonitoringAlert } from "@/types/monitoringAlerts"

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

<style lang="scss" scoped>
.monitoring-alerts-item {
	border-top: var(--border-small-050);
	transition: all 0.2s var(--bezier-ease);
	min-height: 100px;

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;
		}
	}

	.main-box {
		word-break: break-word;
	}

	.footer-box {
		font-size: 13px;
		margin-top: 10px;
		display: none;
	}

	&:not(.embedded) {
		border-radius: var(--border-radius);
		background-color: var(--bg-color);
		border: var(--border-small-050);

		&:hover {
			border-color: var(--primary-color);
		}
	}

	@container (max-width: 550px) {
		.main-box {
			.actions-box {
				display: none;
			}
		}

		.footer-box {
			display: flex;
		}
	}
}
</style>
