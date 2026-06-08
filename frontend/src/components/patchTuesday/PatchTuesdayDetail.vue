<template>
	<div class="@container flex flex-col gap-3">
		<CardEntity size="small" embedded highlighted :status="priorityCardStatus">
			<template #headerMain>
				<span class="text-default font-mono font-semibold">{{ item.cve }}</span>
			</template>
			<template #headerExtra>
				<div class="flex flex-wrap items-center justify-end gap-2">
					<PatchTuesdayPriorityBadge :priority="item.prioritization.priority" />
					<Badge
						v-if="item.kev.in_kev"
						type="splitted"
						bright
						color="danger"
						size="small"
						class="text-default"
					>
						<template #label>
							<Icon :name="AlertIcon" :size="12" />
							KEV
						</template>
					</Badge>
					<Badge
						v-if="item.severity"
						type="splitted"
						bright
						size="small"
						:color="severityBadgeColor"
						class="text-default"
					>
						<template #label>{{ item.severity }}</template>
					</Badge>
				</div>
			</template>
			<template #default>
				<p class="text-base leading-snug font-medium">
					{{ item.title || "No title available" }}
				</p>
			</template>
			<template #footerMain>
				<div class="flex flex-wrap items-center gap-2">
					<Badge type="splitted" bright size="small">
						<template #label>Cycle</template>
						<template #value>{{ item.cycle }}</template>
					</Badge>
					<Badge type="splitted" bright size="small">
						<template #label>Release</template>
						<template #value>{{ item.release_type }}</template>
					</Badge>
					<Badge type="splitted" bright size="small">
						<template #label>Updated</template>
						<template #value>
							{{ formatDate(item.timestamp_utc, dFormats.datetime, { tz: true }) }}
						</template>
					</Badge>
				</div>
			</template>
		</CardEntity>

		<CardEntity size="small" embedded main-box-class="gap-2">
			<template #headerMain>Risk Scores</template>
			<template #default>
				<div class="flex flex-col gap-2">
					<div class="grid grid-cols-1 gap-2 @lg:grid-cols-3">
						<CardLink
							v-if="item.cvss.base !== null"
							size="small"
							title="CVSS Base"
							:value="item.cvss.base.toFixed(1)"
							subtitle="Base score"
							:color="cvssBadgeColor"
						/>
						<CardLink
							v-if="item.epss.score !== null"
							size="small"
							title="EPSS"
							:value="`${(item.epss.score * 100).toFixed(2)}%`"
							subtitle="Exploit probability"
							color="warning"
						/>
						<CardLink
							v-if="item.epss.percentile !== null"
							size="small"
							title="EPSS Percentile"
							:value="`${(item.epss.percentile * 100).toFixed(0)}%`"
							subtitle="vs. all CVEs"
							color="warning"
						/>
					</div>
					<CardKV v-if="item.cvss.vector" class="@sm:col-span-3">
						<template #key>CVSS Vector</template>
						<template #value>{{ item.cvss.vector }}</template>
					</CardKV>
				</div>
			</template>
		</CardEntity>

		<CardEntity size="small" embedded :status="priorityCardStatus" main-box-class="gap-2">
			<template #headerMain>Prioritization</template>
			<template #default>
				<div class="grid grid-cols-1 gap-2">
					<CardKV :color="priorityKvColor">
						<template #key>Suggested SLA</template>
						<template #value>{{ item.prioritization.suggested_sla }}</template>
					</CardKV>
					<CardKV v-if="item.prioritization.reason.length > 0">
						<template #key>Priority factors</template>
						<template #value>
							<ul class="text-secondary list-disc space-y-0.5 pl-4 text-sm">
								<li v-for="reason in item.prioritization.reason" :key="reason">{{ reason }}</li>
							</ul>
						</template>
					</CardKV>
				</div>
			</template>
		</CardEntity>

		<CardEntity size="small" embedded main-box-class="gap-2">
			<template #headerMain>Affected Product</template>
			<template #default>
				<div class="grid grid-cols-1 gap-2 @md:grid-cols-2">
					<CardKV>
						<template #key>Product</template>
						<template #value>{{ item.affected.product }}</template>
					</CardKV>
					<CardKV>
						<template #key>Family</template>
						<template #value>{{ item.affected.family }}</template>
					</CardKV>
					<CardKV v-if="item.affected.component_hint" class="@md:col-span-2">
						<template #key>Component</template>
						<template #value>{{ item.affected.component_hint }}</template>
					</CardKV>
				</div>
			</template>
		</CardEntity>

		<CardEntity v-if="item.kev.in_kev" size="small" embedded status="error" main-box-class="gap-2">
			<template #headerMain>CISA KEV</template>
			<template #headerExtra>
				<Badge type="splitted" bright color="danger" size="small" class="text-default">
					<template #label>
						<Icon :name="AlertIcon" :size="12" />
						Exploited
					</template>
				</Badge>
			</template>
			<template #default>
				<div class="grid grid-cols-1 gap-2 @md:grid-cols-2">
					<CardKV v-if="item.kev.due_date" color="danger">
						<template #key>Remediation Due</template>
						<template #value>{{ formatDate(item.kev.due_date, dFormats.date) }}</template>
					</CardKV>
					<CardKV v-if="item.kev.date_added">
						<template #key>Date Added</template>
						<template #value>{{ formatDate(item.kev.date_added, dFormats.date) }}</template>
					</CardKV>
					<CardKV v-if="item.kev.known_ransomware_campaign_use" class="col-span-full">
						<template #key>Ransomware Use</template>
						<template #value>{{ item.kev.known_ransomware_campaign_use }}</template>
					</CardKV>
					<CardKV v-if="item.kev.required_action" class="@md:col-span-2">
						<template #key>Required Action</template>
						<template #value>{{ item.kev.required_action }}</template>
					</CardKV>
					<CardKV v-if="item.kev.short_description" class="@md:col-span-2">
						<template #key>Description</template>
						<template #value>{{ item.kev.short_description }}</template>
					</CardKV>
				</div>
			</template>
		</CardEntity>

		<CardEntity size="small" embedded main-box-class="gap-2">
			<template #headerMain>Remediation</template>
			<template #default>
				<div v-if="item.remediation.kbs.length > 0" class="flex flex-wrap gap-2">
					<Badge
						v-for="kb in item.remediation.kbs"
						:key="kb"
						type="splitted"
						bright
						size="small"
						class="cursor-pointer"
						@click="openKB(kb)"
					>
						<template #label>
							<Icon :name="ExternalLinkIcon" :size="12" />
							KB
						</template>
						<template #value>{{ kb }}</template>
					</Badge>
				</div>
				<n-empty v-else description="No KB articles available" size="small" class="min-h-16 justify-center" />
			</template>
		</CardEntity>

		<CardEntity size="small" embedded main-box-class="gap-2">
			<template #headerMain>Sources</template>
			<template #default>
				<div class="grid grid-cols-1 gap-2">
					<CardKV>
						<template #key>MSRC</template>
						<template #value>
							<a
								:href="item.source.msrc_cvrf_url"
								target="_blank"
								rel="noopener noreferrer"
								class="text-primary inline-flex items-center gap-1 hover:underline"
							>
								Security Update
								<Icon :name="ExternalLinkIcon" :size="12" />
							</a>
						</template>
					</CardKV>
					<CardKV>
						<template #key>NVD</template>
						<template #value>
							<a
								:href="`https://nvd.nist.gov/vuln/detail/${item.cve}`"
								target="_blank"
								rel="noopener noreferrer"
								class="text-primary inline-flex items-center gap-1 hover:underline"
							>
								{{ item.cve }}
								<Icon :name="ExternalLinkIcon" :size="12" />
							</a>
						</template>
					</CardKV>
					<CardKV v-if="item.kev.in_kev">
						<template #key>CISA KEV</template>
						<template #value>
							<a
								:href="item.source.cisa_kev_url"
								target="_blank"
								rel="noopener noreferrer"
								class="text-error inline-flex items-center gap-1 hover:underline"
							>
								KEV Catalog
								<Icon :name="ExternalLinkIcon" :size="12" />
							</a>
						</template>
					</CardKV>
				</div>
			</template>
		</CardEntity>
	</div>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { PatchTuesdayItem } from "@/types/patchTuesday.d"
import { NEmpty } from "naive-ui"
import { computed, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { PriorityLevel } from "@/types/patchTuesday.d"
import { formatDate } from "@/utils/format"
import PatchTuesdayPriorityBadge from "./PatchTuesdayPriorityBadge.vue"

const props = defineProps<{
	item: PatchTuesdayItem
}>()

const { item } = toRefs(props)

const dFormats = useSettingsStore().dateFormat
const AlertIcon = "carbon:warning"
const ExternalLinkIcon = "carbon:launch"

const severityBadgeColor = computed((): BadgeColor | undefined => {
	const severity = item.value.severity?.toLowerCase()
	if (severity === "critical") return "danger"
	if (severity === "important") return "warning"
	if (severity === "low") return "success"
	return undefined
})

const cvssBadgeColor = computed((): BadgeColor | undefined => {
	const score = item.value.cvss.base
	if (score === null) return undefined
	if (score >= 9) return "danger"
	if (score >= 7) return "warning"
	if (score >= 4) return "primary"
	return "success"
})

const priorityCardStatus = computed(() => {
	switch (item.value.prioritization.priority) {
		case PriorityLevel.P0:
			return "error"
		case PriorityLevel.P1:
			return "warning"
		case PriorityLevel.P3:
			return "success"
		default:
			return undefined
	}
})

const priorityKvColor = computed((): "danger" | "warning" | "success" | "primary" | undefined => {
	switch (item.value.prioritization.priority) {
		case PriorityLevel.P0:
			return "danger"
		case PriorityLevel.P1:
			return "warning"
		case PriorityLevel.P3:
			return "success"
		default:
			return "primary"
	}
})

function openKB(kb: string) {
	window.open(`https://support.microsoft.com/help/${kb.replace("KB", "")}`, "_blank")
}
</script>
