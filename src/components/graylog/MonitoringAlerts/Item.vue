<template>
	<div class="item flex flex-col gap-2 px-5 py-3">
		<div class="header-box flex justify-between gap-4">
			<div class="name">{{ alert.name }}</div>
			<div class="badge flex mb-2">
				<Badge :type="isEnabled ? 'active' : 'muted'">
					<template #iconRight>
						<Icon :name="isEnabled ? EnabledIcon : DisabledIcon" :size="13"></Icon>
					</template>
					<template #label>
						<span class="whitespace-nowrap">
							{{ isEnabled ? "Enabled" : "Not Enabled" }}
						</span>
					</template>
				</Badge>
			</div>
		</div>
		<div class="main-box flex justify-between gap-4">
			<div class="content">{{ alert.value }}</div>
			<div class="actions-box">
				<n-button v-if="!isEnabled" :loading="loadingProvision" type="success" secondary>
					<template #icon><Icon :name="EnableIcon"></Icon></template>
					Enable
				</n-button>
			</div>
		</div>
		<div class="footer-box flex justify-between items-center gap-4">
			<div class="actions-box">
				<n-button v-if="!isEnabled" :loading="loadingProvision" type="success" secondary size="small">
					<template #icon><Icon :name="EnableIcon"></Icon></template>
					Enable
				</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AvailableMonitoringAlert } from "@/types/monitoringAlerts"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { NButton, useDialog, useMessage } from "naive-ui"

const emit = defineEmits<{
	(e: "provisioned"): void
}>()

const { alert } = defineProps<{ alert: AvailableMonitoringAlert }>()

const DisabledIcon = "carbon:subtract"
const EnabledIcon = "ph:check-bold"
const EnableIcon = "carbon:play"

const isEnabled = ref(false)
const loadingProvision = ref(false)
</script>

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

	.header-box {
		font-size: 13px;

		.name {
			font-family: var(--font-family-mono);
			word-break: break-word;
			color: var(--fg-secondary-color);
		}
	}
	.main-box {
		.content {
			word-break: break-word;
		}
	}

	.footer-box {
		display: none;
		font-size: 13px;
		margin-top: 10px;
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}

	@container (max-width: 450px) {
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
