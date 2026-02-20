<template>
	<div class="h-full">
		<CardEntity
			hoverable
			clickable
			:embedded
			class="h-full"
			main-box-class="grow"
			card-entity-wrapper-class="h-full"
			header-box-class="flex-nowrap! items-start"
			@click.stop="showDetails = true"
		>
			<template #headerMain>{{ rule.name }}</template>
			<template #headerExtra>
				<PlatformBadge :platform="rule.platform" />
			</template>
			<template #default>
				<div class="line-clamp-3 text-sm">
					{{ rule.description }}
				</div>
			</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-2">
					<SeverityBadge :severity="rule.severity" />

					<Badge v-if="rule.status" :color="getStatusColor(rule.status)">
						<template #value>{{ rule.status }}</template>
					</Badge>

					<Badge v-if="rule.type" type="splitted">
						<template #label>type</template>
						<template #value>{{ rule.type }}</template>
					</Badge>

					<div v-if="rule.mitre_attack_id?.length" class="flex items-center gap-1">
						<Badge v-for="mitre of rule.mitre_attack_id.slice(0, 2)" :key="mitre" size="small" color="primary">
							<template #value>{{ mitre }}</template>
						</Badge>
						<Badge v-if="rule.mitre_attack_id.length > 2" size="small">
							<template #value>+{{ rule.mitre_attack_id.length - 2 }}</template>
						</Badge>
					</div>
				</div>
			</template>
			<template #footerExtra>
				<n-button size="small" type="primary" secondary @click.stop="showExecuteModal = true">
					<template #icon>
						<Icon :name="PlayIcon" />
					</template>
					Execute
				</n-button>
			</template>
		</CardEntity>

		<!-- Rule Details Modal -->
		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(900px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="`Detection Rule: ${rule.name}`"
			:bordered="false"
			segmented
		>
			<RuleCardContent :rule-id="rule.id" />
		</n-modal>

		<!-- Execute Search Modal -->
		<n-modal
			v-model:show="showExecuteModal"
			preset="card"
			:style="{ maxWidth: 'min(700px, 90vw)' }"
			:bordered="false"
			display-directive="show"
			segmented
		>
			<template #header>
				<div class="flex flex-col gap-2">
					<div class="flex gap-2">
						<PlatformBadge :platform="rule.platform" />
						<SeverityBadge :severity="rule.severity" />
					</div>
					<span class="px-1 text-base">{{ rule.name }}</span>
				</div>
			</template>
			<ExecuteSearchForm :rule-id="rule.id" @success="handleExecuteSuccess" @close="showExecuteModal = false" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { RuleSummary } from "@/types/copilotSearches.d"
import { NButton, NModal, useMessage } from "naive-ui"
import { ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import ExecuteSearchForm from "./ExecuteSearchForm.vue"
import PlatformBadge from "./PlatformBadge.vue"
import RuleCardContent from "./RuleCardContent.vue"
import SeverityBadge from "./SeverityBadge.vue"

const { rule } = defineProps<{ rule: RuleSummary; embedded?: boolean }>()

const showDetails = ref(false)
const showExecuteModal = ref(false)
const message = useMessage()
const PlayIcon = "carbon:play"

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
</script>
