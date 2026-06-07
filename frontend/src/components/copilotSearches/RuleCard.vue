<template>
	<div class="relative h-full">
		<CardEntity
			size="small"
			hoverable
			clickable
			:highlighted="selected"
			:embedded
			class="h-full"
			@click.stop="showDetails = true"
		>
			<template #headerMain>
				<div class="flex flex-wrap gap-2">
					<n-checkbox
						v-if="selectable"
						:checked="selected"
						@update:checked="emit('update:selected', $event)"
						@click.stop
					/>
					<p class="text-default relative -top-0.5 line-clamp-2 flex-1 text-sm leading-snug font-semibold">
						{{ rule.name }}
					</p>
				</div>
			</template>

			<template #default>
				<div class="flex flex-col gap-2">
					<p v-if="rule.description" class="text-secondary line-clamp-3 text-xs leading-relaxed">
						{{ rule.description }}
					</p>
					<p v-else class="text-secondary text-xs italic">No description available</p>
					<div class="flex flex-wrap items-center gap-1.5">
						<n-tag v-if="provisioned" size="small" type="success" round :bordered="false">In Graylog</n-tag>
						<n-tag v-if="rule.has_graylog_query" size="small" round :bordered="false">Query ready</n-tag>
					</div>
				</div>
			</template>

			<template #mainExtra>
				<div class="flex flex-col gap-2">
					<span class="text-secondary text-[10px] font-medium tracking-wider uppercase">Metadata</span>
					<div class="flex flex-wrap items-center gap-1.5">
						<SeverityBadge v-if="rule.severity" :severity="rule.severity" size="small" />

						<Badge v-if="rule.status" size="small" :color="getStatusColor(rule.status)">
							<template #label>status</template>
							<template #value>{{ rule.status }}</template>
						</Badge>

						<Badge v-if="rule.type" type="splitted" size="small">
							<template #label>type</template>
							<template #value>{{ rule.type }}</template>
						</Badge>

						<Badge type="splitted" size="small">
							<template #iconLeft>
								<Icon :name="platformInfo.icon" :size="11" />
							</template>
							<template #label>platform</template>
							<template #value>{{ platformInfo.label }}</template>
						</Badge>

						<Badge v-for="mitre of visibleMitreIds" :key="mitre" size="small" color="primary">
							<template #value>{{ mitre }}</template>
						</Badge>
						<Badge v-if="hiddenMitreCount > 0" size="small">
							<template #value>+{{ hiddenMitreCount }}</template>
						</Badge>
					</div>
				</div>
			</template>

			<template #footer>
				<div class="flex w-full items-center justify-end gap-2">
					<n-button
						v-if="rule.has_graylog_query"
						size="small"
						secondary
						@click.stop="showProvisionModal = true"
					>
						<template #icon>
							<Icon :name="ProvisionIcon" />
						</template>
						Provision
					</n-button>
					<n-button size="small" type="primary" @click.stop="showExecuteModal = true">
						<template #icon>
							<Icon :name="PlayIcon" />
						</template>
						Execute
					</n-button>
				</div>
			</template>
		</CardEntity>

		<!-- Rule Details Modal -->
		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(750px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			title="Detection Rule"
			:bordered="false"
			segmented
		>
			<RuleCardContent :rule-id="rule.id" />
		</n-modal>

		<!-- Execute Search Modal -->
		<n-modal
			v-model:show="showExecuteModal"
			preset="card"
			:style="{ maxWidth: 'min(550px, 90vw)' }"
			title="Execute Search"
			:bordered="false"
			display-directive="show"
			segmented
		>
			<ExecuteSearchForm
				:rule-id="rule.id"
				show-header
				@success="handleExecuteSuccess"
				@close="showExecuteModal = false"
			/>
		</n-modal>

		<!-- Provision Graylog Alert Modal -->
		<n-modal
			v-model:show="showProvisionModal"
			preset="card"
			:style="{ maxWidth: 'min(550px, 90vw)' }"
			title="Provision Graylog Alert"
			:bordered="false"
			display-directive="show"
			segmented
		>
			<ProvisionGraylogForm
				:rule-id="rule.id"
				@success="handleProvisionSuccess"
				@close="showProvisionModal = false"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { RuleSummary } from "@/types/copilotSearches.d"
import { NButton, NCheckbox, NModal, NTag, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import ExecuteSearchForm from "./ExecuteSearchForm.vue"
import ProvisionGraylogForm from "./ProvisionGraylogForm.vue"
import RuleCardContent from "./RuleCardContent.vue"
import SeverityBadge from "./SeverityBadge.vue"

const { rule } = defineProps<{
	rule: RuleSummary
	embedded?: boolean
	provisioned?: boolean
	selectable?: boolean
	selected?: boolean
}>()

const emit = defineEmits<{
	(e: "update:selected", value: boolean): void
}>()

const showDetails = ref(false)
const showExecuteModal = ref(false)
const showProvisionModal = ref(false)
const message = useMessage()

const PlayIcon = "carbon:play"
const ProvisionIcon = "carbon:add-alt"

const visibleMitreIds = computed(() => rule.mitre_attack_id?.slice(0, 2) ?? [])
const hiddenMitreCount = computed(() => Math.max((rule.mitre_attack_id?.length ?? 0) - 2, 0))

// Platform → icon + label mapping. Mirrors the platforms the CoPilot Searches
// backend actually emits (linux, windows, powershell, cve, unknown). Done
// locally instead of using the shared PlatformBadge so we cover values like
// "powershell" and "cve" that the shared `getOS` util doesn't recognize.
const PLATFORM_INFO: Record<string, { icon: string; label: string }> = {
	linux: { icon: "mdi:linux", label: "Linux" },
	windows: { icon: "mdi:microsoft-windows", label: "Windows" },
	powershell: { icon: "mdi:powershell", label: "PowerShell" },
	cve: { icon: "carbon:security", label: "CVE" }
}
const platformInfo = computed(() => {
	const key = (rule.platform || "").toLowerCase()
	return PLATFORM_INFO[key] || { icon: "mdi:help-box", label: "Unknown" }
})

function getStatusColor(status: string): BadgeColor | undefined {
	switch (status.toLowerCase()) {
		case "production":
			return "success"
		case "experimental":
			return "warning"
		case "deprecated":
			return "danger"
		default:
			return undefined
	}
}

function handleExecuteSuccess() {
	showExecuteModal.value = false
	message.success("Search executed successfully!")
}

function handleProvisionSuccess() {
	showProvisionModal.value = false
}
</script>
