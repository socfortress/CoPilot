<template>
	<n-spin :show="loading" class="min-h-50">
		<div v-if="rule" class="flex flex-col gap-4">
			<CardEntity :status="hitsCardStatus">
				<template #headerMain>
					<div class="flex items-center gap-3">
						<n-tag
							size="large"
							:type="levelTagType(rule.level)"
							:bordered="false"
							class="flex min-h-10 min-w-10 items-center justify-center font-mono font-bold"
						>
							{{ rule.level ?? "—" }}
						</n-tag>
						<div class="flex flex-col gap-0.5">
							<div class="text-secondary text-xs tracking-wide uppercase">Wazuh Rule</div>
							<div class="text-default text-lg leading-tight font-semibold">Rule {{ rule.id }}</div>
						</div>
					</div>
				</template>

				<template #default>
					<div class="flex flex-col gap-2">
						<div v-if="rule.description">
							{{ rule.description }}
						</div>
						<div class="flex flex-wrap gap-2">
							<Badge v-if="rule.status" type="splitted" color="success">
								<template #label>Status</template>
								<template #value>{{ rule.status }}</template>
							</Badge>
							<Badge v-if="rule.firing_stats_available" type="splitted" :color="hitsBadgeColor">
								<template #label>Hits 30d</template>
								<template #value>{{ rule.hits_30d.toLocaleString() }}</template>
							</Badge>
							<Badge v-if="rule.firing_stats_available" type="splitted">
								<template #label>Hits 7d</template>
								<template #value>{{ rule.hits_7d.toLocaleString() }}</template>
							</Badge>
							<Badge v-if="rule.firing_stats_available && rule.last_seen" type="splitted" color="primary">
								<template #label>Last fired</template>
								<template #value>{{ formatRelativeTime(rule.last_seen) }}</template>
							</Badge>
							<Badge v-if="rule.filename" type="splitted">
								<template #label>File</template>
								<template #value>{{ rule.filename }}</template>
							</Badge>
						</div>
					</div>
				</template>
			</CardEntity>

			<!-- Groups -->
			<CardEntity v-if="rule.groups.length">
				<template #headerMain>
					<SectionLabel icon="carbon:tag" label="Groups" />
				</template>
				<template #default>
					<div class="flex flex-wrap gap-1.5">
						<n-tag v-for="g of rule.groups" :key="g" size="small" type="primary">
							{{ g }}
						</n-tag>
					</div>
				</template>
			</CardEntity>

			<!-- MITRE ATT&CK -->
			<CardEntity v-if="rule.mitre.length">
				<template #headerMain>
					<SectionLabel icon="carbon:flag" label="MITRE ATT&CK" />
				</template>
				<template #default>
					<div class="flex flex-col gap-2">
						<div v-if="rule.mitre.length" class="flex flex-wrap gap-1.5">
							<n-tag v-for="t of rule.mitre" :key="t" size="small" type="warning">
								{{ t }}
							</n-tag>
						</div>
					</div>
				</template>
			</CardEntity>

			<CardEntity v-if="rule.tactics.length">
				<template #headerMain>
					<SectionLabel icon="carbon:radar" label="Tactics" />
				</template>
				<template #default>
					<div class="flex flex-col gap-2">
						<div v-if="rule.tactics.length" class="flex flex-wrap gap-1.5">
							<n-tag v-for="t of rule.tactics" :key="t" size="small">
								{{ t.toUpperCase() }}
							</n-tag>
						</div>
					</div>
				</template>
			</CardEntity>

			<!-- Compliance — only render frameworks that actually have values. -->
			<CardEntity v-if="hasCompliance">
				<template #headerMain>
					<SectionLabel icon="carbon:certificate-check" label="Compliance" />
				</template>
				<template #default>
					<div class="divide-border flex flex-col gap-0 divide-y">
						<div v-for="[key, values] of complianceEntries" :key class="flex items-start gap-3 py-2">
							<div
								class="text-secondary w-28 shrink-0 pt-0.5 text-xs font-semibold tracking-wide uppercase"
							>
								{{ key }}
							</div>
							<div class="flex flex-wrap gap-1">
								<n-tag v-for="v of values" :key="v" size="small">
									{{ v }}
								</n-tag>
							</div>
						</div>
					</div>
				</template>
			</CardEntity>

			<CardEntity v-if="rule.source_xml">
				<template #header>
					<SectionLabel icon="carbon:code" label="Rule Source" />
				</template>
				<template #default>
					<CodeSource :code="rule.source_xml" />
				</template>
			</CardEntity>

			<!-- File location footer -->
			<CardEntity v-if="rule.relative_dirname" embedded>
				<template #default>
					<div class="flex items-center gap-2 text-xs">
						<Icon name="carbon:folder" :size="12" />
						<span class="text-secondary">Location:</span>
						<code class="font-mono">{{ rule.relative_dirname }}/{{ rule.filename }}</code>
					</div>
				</template>
			</CardEntity>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { TagProps } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { CatalogWazuhRuleDetailResponse } from "@/types/detection-catalog"
import { NSpin, NTag, useMessage } from "naive-ui"
import { computed, defineComponent, h, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CodeSource from "@/components/common/CodeSource.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import dayjs from "@/utils/dayjs"

const props = defineProps<{ ruleId: number }>()

const SectionLabel = defineComponent({
	props: { icon: String, label: String },
	setup(props) {
		return () =>
			h("div", { class: "flex items-center gap-2" }, [
				props.icon ? h(Icon, { name: props.icon, size: 14 }) : null,
				h("span", { class: "text-secondary text-xs font-semibold tracking-wide uppercase" }, props.label)
			])
	}
})

const message = useMessage()

const rule = ref<CatalogWazuhRuleDetailResponse | null>(null)
const loading = ref(false)

// Severity classes for the big hero level badge — same buckets as the
// index column. Single source of truth at the top so they stay in sync.
function levelTagType(level: number | null | undefined): TagProps["type"] {
	if (level === null || level === undefined) return "default"
	if (level >= 12) return "error"
	if (level >= 7) return "warning"
	if (level >= 3) return "info"
	return "default"
}

// Pick a card status tint for the hero based on hit volume — lets the modal
// signal "this rule is hot right now" without screaming.
const hitsCardStatus = computed<"success" | "warning" | "error" | undefined>(() => {
	if (!rule.value?.firing_stats_available) return undefined
	const h = rule.value.hits_30d
	if (h >= 10000) return "error"
	if (h >= 1000) return "warning"
	return undefined
})

const hitsBadgeColor = computed<"danger" | "warning" | "primary" | "success" | undefined>(() => {
	const h = rule.value?.hits_30d
	if (h === undefined || h === 0) return undefined
	if (h >= 10000) return "danger"
	if (h >= 1000) return "warning"
	if (h >= 100) return "primary"
	return "success"
})

const complianceEntries = computed<[string, string[]][]>(() => {
	const c = rule.value?.compliance
	if (!c) return []
	const labels: Record<string, string> = {
		pci_dss: "PCI DSS",
		gdpr: "GDPR",
		hipaa: "HIPAA",
		nist_800_53: "NIST 800-53",
		tsc: "TSC",
		gpg13: "GPG13"
	}
	return Object.entries(c)
		.filter(([, v]) => Array.isArray(v) && v.length > 0)
		.map(([k, v]) => [labels[k] ?? k, v as string[]])
})

const hasCompliance = computed(() => complianceEntries.value.length > 0)

function formatRelativeTime(iso: string): string {
	return dayjs(iso).fromNow()
}

function load(id: number) {
	loading.value = true
	rule.value = null
	Api.detectionCatalog
		.getWazuhRule(id)
		.then(res => {
			if (res.data?.success) rule.value = res.data
			else message.warning(res.data?.message || "Failed to load Wazuh rule detail")
		})
		.catch(err => {
			const status = err.response?.status
			if (status === 404) {
				message.warning(`Wazuh rule ${id} not found in the cache`)
			} else {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to load Wazuh rule detail")
			}
		})
		.finally(() => {
			loading.value = false
		})
}

watch(
	() => props.ruleId,
	id => load(id)
)
onBeforeMount(() => load(props.ruleId))
</script>
