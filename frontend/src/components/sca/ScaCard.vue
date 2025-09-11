<template>
	<div class="sca-card h-full">
		<CardEntity hoverable clickable :embedded class="@container h-full flex flex-col" :class="getComplianceBorderClass(sca.score)" @click.stop="showDetails = true">
			<template #headerMain>{{ sca.policy_name }}</template>
			<template #headerExtra>
				<Badge :color="getComplianceLevelColor(getComplianceLevel(sca.score))">
					<template #iconLeft><Icon :name="getComplianceLevelIcon(getComplianceLevel(sca.score))" :size="14" /></template>
					<template #value>{{ getComplianceLevel(sca.score) }}</template>
				</Badge>
			</template>
			<template #default>
				<div class="flex-1">
					<p class="text-base font-medium opacity-90 leading-relaxed line-clamp-3">{{ sca.description }}</p>
					<div class="mt-2 text-sm opacity-75">
						<div class="flex items-center gap-2">
							<Icon :name="HostIcon" :size="14" />
							<span>{{ sca.agent_name }}</span>
						</div>
						<div class="flex items-center gap-2 mt-1">
							<Icon :name="PolicyIcon" :size="14" />
							<span>{{ sca.policy_id }}</span>
						</div>
					</div>
				</div>
			</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-2">
					<Badge v-if="sca.customer_code" class="text-xs">
						<template #value>{{ sca.customer_code }}</template>
					</Badge>

					<Badge color="primary" type="splitted" class="text-xs">
						<template #label>Score</template>
						<template #value>{{ sca.score }}%</template>
					</Badge>

					<Badge color="success" type="splitted" class="text-xs">
						<template #label>Pass</template>
						<template #value>{{ sca.pass_count }}</template>
					</Badge>

					<Badge color="danger" type="splitted" class="text-xs">
						<template #label>Fail</template>
						<template #value>{{ sca.fail_count }}</template>
					</Badge>

					<Badge v-if="sca.invalid_count > 0" color="warning" type="splitted" class="text-xs">
						<template #label>Invalid</template>
						<template #value>{{ sca.invalid_count }}</template>
					</Badge>

					<Badge type="splitted" class="text-xs">
						<template #label>Total</template>
						<template #value>{{ sca.total_checks }}</template>
					</Badge>
				</div>
			</template>
			<template #footerExtra>
				<div class="text-xs opacity-60">
					{{ formatDate(sca.end_scan) }}
				</div>
			</template>
		</CardEntity>

		<!-- SCA Details Modal -->
		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)' }"
			:title="`SCA Policy: ${sca.policy_name}`"
			:bordered="false"
			segmented
		>
			<ScaCardContent :sca="sca" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AgentScaOverviewItem } from "@/types/sca.d"
import { NModal } from "naive-ui"
import { ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getComplianceLevel, getComplianceLevelColor, getComplianceLevelIcon } from "@/types/sca.d"
import ScaCardContent from "./ScaCardContent.vue"

const { sca } = defineProps<{ sca: AgentScaOverviewItem; embedded?: boolean }>()

const showDetails = ref(false)
const HostIcon = "carbon:bare-metal-server"
const PolicyIcon = "carbon:security"

function getComplianceBorderClass(score: number): string {
	const level = getComplianceLevel(score)
	const borderMap: Record<string, string> = {
		Excellent: "border-l-4 border-l-green-500 dark:border-l-green-400",
		Good: "border-l-4 border-l-blue-500 dark:border-l-blue-400",
		Average: "border-l-4 border-l-yellow-500 dark:border-l-yellow-400",
		Poor: "border-l-4 border-l-orange-500 dark:border-l-orange-400",
		Critical: "border-l-4 border-l-red-500 dark:border-l-red-400"
	}
	return borderMap[level] || ""
}

function formatDate(dateString: string): string {
	return new Date(dateString).toLocaleDateString()
}
</script>

<style scoped>
.sca-card {
	min-height: 280px;
}

.line-clamp-3 {
	display: -webkit-box;
	-webkit-line-clamp: 3;
	line-clamp: 3;
	-webkit-box-orient: vertical;
	overflow: hidden;
	text-overflow: ellipsis;
}
</style>
