<template>
	<div class="h-full">
		<CardEntity
			clickable
			:embedded
			class="h-full"
			main-box-class="grow"
			card-entity-wrapper-class="h-full"
			header-box-class="flex-nowrap! items-start"
			:class="`${getComplianceBorderClass(sca.score)} transition-all duration-300`"
			@click.stop="showDetails = true"
		>
			<template #headerMain>{{ sca.policy_name }}</template>
			<template #headerExtra>
				<ScaLevelBadge :score="sca.score" />
			</template>
			<template #default>
				<div class="flex flex-col gap-4">
					<div class="leading-snug font-medium">
						{{ sca.description }}
					</div>
					<div class="text-secondary flex flex-col gap-0.5 text-sm">
						<div class="flex items-center gap-2">
							<Icon :name="HostIcon" :size="14" />
							<span>{{ sca.agent_name }}</span>
						</div>
						<div class="mt-1 flex items-center gap-2">
							<Icon :name="PolicyIcon" :size="14" />
							<span>{{ sca.policy_id }}</span>
						</div>
					</div>
				</div>
			</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-2">
					<Badge type="splitted" class="text-xs">
						<template #label>Total</template>
						<template #value>{{ sca.total_checks }}</template>
					</Badge>

					<Badge color="success" type="splitted" class="text-xs">
						<template #label>Pass</template>
						<template #value>{{ sca.pass }}</template>
					</Badge>

					<Badge color="danger" type="splitted" class="text-xs">
						<template #label>Fail</template>
						<template #value>{{ sca.fail }}</template>
					</Badge>

					<Badge v-if="sca.invalid > 0" color="warning" type="splitted" class="text-xs">
						<template #label>Invalid</template>
						<template #value>{{ sca.invalid }}</template>
					</Badge>

					<Badge v-if="sca.customer_code" class="text-xs">
						<template #value>
							<code
								class="text-primary cursor-pointer"
								@click.stop="gotoCustomer({ code: sca.customer_code })"
							>
								customer #{{ sca.customer_code }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</template>
					</Badge>
				</div>
			</template>
			<template #footerExtra>
				<div class="text-tertiary text-xs">
					{{ formatDate(sca.end_scan, dFormats.datetime) }}
				</div>
			</template>
		</CardEntity>

		<!-- SCA Details Modal -->
		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(500px, 90vh)' }"
			:title="`SCA Policy: ${sca.policy_name}`"
			:bordered="false"
			content-class="p-0!"
			segmented
		>
			<ScaCardContent :sca />
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
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import ScaCardContent from "./ScaCardContent.vue"
import ScaLevelBadge from "./ScaLevelBadge.vue"
import { getComplianceLevel } from "./utils"

const { sca } = defineProps<{ sca: AgentScaOverviewItem; embedded?: boolean }>()

const { gotoCustomer } = useGoto()
const dFormats = useSettingsStore().dateFormat

const showDetails = ref(false)
const LinkIcon = "carbon:launch"
const HostIcon = "carbon:bare-metal-server"
const PolicyIcon = "carbon:security"

function getComplianceBorderClass(score: number): string {
	const level = getComplianceLevel(score)
	const borderMap: Record<string, string> = {
		Excellent: "ring-1 ring-success/30 hover:ring-success/80",
		Good: "ring-1 ring-info/30 hover:ring-info/80",
		Average: "ring-1 ring-warning/30 hover:ring-warning/80",
		Poor: "ring-1 ring-orange-500/30 hover:ring-orange-500/80",
		Critical: "ring-1 ring-error/30 hover:ring-error/80"
	}
	return borderMap[level] || ""
}
</script>
