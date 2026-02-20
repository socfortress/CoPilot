<template>
	<n-spin :show="loading">
		<div v-if="rule" class="flex flex-col gap-4 pb-1">
			<!-- Basic Information -->
			<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
				<CardKV>
					<template #key>Information</template>
					<template #value>
						<div class="flex flex-col gap-2 py-0.5">
							<div class="flex flex-wrap gap-2">
								<strong>Author:</strong>
								<span>{{ rule.author }}</span>
							</div>
							<div class="flex flex-wrap gap-2">
								<strong>Version:</strong>
								<span>{{ rule.version }}</span>
							</div>
							<div class="flex flex-wrap gap-2">
								<strong>Date:</strong>
								<span>{{ rule.date }}</span>
							</div>
							<div class="flex flex-wrap gap-2">
								<strong>Status:</strong>
								<Badge :color="getStatusColor(rule.status)" size="small">
									<template #value>{{ rule.status }}</template>
								</Badge>
							</div>
							<div class="flex flex-wrap gap-2">
								<strong>Type:</strong>
								<span>{{ rule.type }}</span>
							</div>
						</div>
					</template>
				</CardKV>
				<CardKV>
					<template #key>Risk Assessment</template>
					<template #value>
						<div class="flex flex-col gap-2 py-0.5">
							<div class="flex flex-wrap items-center gap-2">
								<strong>Severity:</strong>
								<SeverityBadge :severity="rule.response.severity" />
							</div>
							<div class="flex flex-wrap gap-2">
								<strong>Risk Score:</strong>
								<span>{{ rule.response.risk_score }}</span>
							</div>
							<div class="flex flex-wrap gap-2">
								<strong>Platform:</strong>
								<PlatformBadge :platform="rule.tags.asset_type" />
							</div>
							<div class="flex flex-wrap gap-2">
								<strong>Security Domain:</strong>
								<span>{{ rule.tags.security_domain }}</span>
							</div>
						</div>
					</template>
				</CardKV>
			</div>

			<!-- Description -->
			<CardKV>
				<template #key>Description</template>
				<template #value>{{ rule.description }}</template>
			</CardKV>

			<!-- MITRE ATT&CK -->
			<CardKV v-if="rule.tags.mitre_attack_id?.length">
				<template #key>MITRE ATT&CK Techniques</template>
				<template #value>
					<div class="flex flex-wrap gap-2">
						<Badge v-for="mitre of rule.tags.mitre_attack_id" :key="mitre" color="primary">
							<template #value>{{ mitre }}</template>
						</Badge>
					</div>
				</template>
			</CardKV>

			<!-- Data Sources -->
			<CardKV v-if="rule.data_source?.length">
				<template #key>Data Sources</template>
				<template #value>
					<div class="flex flex-wrap gap-2">
						<Badge v-for="source of rule.data_source" :key="source">
							<template #value>{{ source }}</template>
						</Badge>
					</div>
				</template>
			</CardKV>

			<!-- Parameters -->
			<CardKV v-if="rule.parameters?.length">
				<template #key>Parameters</template>
				<template #value>
					<div class="grid grid-cols-1 gap-3 py-1 lg:grid-cols-2">
						<CardEntity
							v-for="param in rule.parameters"
							:key="param.name"
							embedded
							size="small"
							class="h-full"
							main-box-class="grow"
							card-entity-wrapper-class="h-full"
						>
							<template #headerMain>
								<div class="text-default flex items-center gap-4">
									<div class="text-sm font-semibold">{{ param.name }}</div>
									<Badge :color="param.required ? 'danger' : 'success'" type="splitted">
										<template #value>
											<span class="text-xs">{{ param.required ? "Required" : "Optional" }}</span>
										</template>
									</Badge>
								</div>
							</template>
							<template #headerExtra>
								<Badge>
									<template #value>
										<span class="text-xs">{{ param.type }}</span>
									</template>
								</Badge>
							</template>

							<template v-if="param.description" #default>
								<p class="text-xs">{{ param.description }}</p>
							</template>

							<template #footer>
								<div class="flex flex-col gap-1">
									<div
										v-if="param.default !== null && param.default !== undefined"
										class="text-xs opacity-60"
									>
										<span class="font-medium">Default:</span>
										<code class="code-block ml-1 rounded px-1 py-0.5 text-xs">
											{{ param.default }}
										</code>
									</div>
									<div
										v-if="param.example !== null && param.example !== undefined"
										class="text-xs opacity-60"
									>
										<span class="font-medium">Example:</span>
										<code class="code-block ml-1 rounded px-1 py-0.5 text-xs">
											{{ param.example }}
										</code>
									</div>
								</div>
							</template>
						</CardEntity>
					</div>
				</template>
			</CardKV>

			<!-- How to Implement -->
			<CardKV v-if="rule.how_to_implement">
				<template #key>How to Implement</template>
				<template #value>{{ rule.how_to_implement }}</template>
			</CardKV>

			<!-- Known False Positives -->
			<CardKV v-if="rule.known_false_positives">
				<template #key>Known False Positives</template>
				<template #value>{{ rule.known_false_positives }}</template>
			</CardKV>

			<!-- References -->
			<CardKV v-if="rule.references?.length">
				<template #key>References</template>
				<template #value>
					<div class="flex flex-col gap-1">
						<a
							v-for="ref of rule.references"
							:key="ref"
							:href="ref"
							target="_blank"
							rel="noopener"
							class="text-sm text-primary-color hover:underline"
						>
							{{ ref }}
						</a>
					</div>
				</template>
			</CardKV>

			<!-- Analytic Stories -->
			<div v-if="rule.tags.analytic_story?.length" class="flex flex-wrap gap-2">
				<code v-for="story of rule.tags.analytic_story" :key="story">#{{ story }}</code>
			</div>
		</div>

		<n-empty v-else-if="!loading" description="Failed to load rule details" />
	</n-spin>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { RuleDetail } from "@/types/copilotSearches.d"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onMounted, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import PlatformBadge from "./PlatformBadge.vue"
import SeverityBadge from "./SeverityBadge.vue"

const { ruleId } = defineProps<{
	ruleId: string
}>()

const loading = ref(false)
const rule = ref<RuleDetail | null>(null)
const message = useMessage()

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

async function loadRule() {
	loading.value = true
	try {
		const res = await Api.copilotSearches.getRuleById(ruleId)
		if (res.data.success) {
			rule.value = res.data.rule
		} else {
			message.error(res.data?.message || "Failed to load rule details")
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to load rule details")
	} finally {
		loading.value = false
	}
}

onMounted(() => {
	loadRule()
})
</script>
