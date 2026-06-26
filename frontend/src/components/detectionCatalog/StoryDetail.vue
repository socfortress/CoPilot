<template>
	<n-spin :show="loading" class="min-h-50">
		<div v-if="story" class="flex flex-col gap-6">
			<CardEntity>
				<template #headerMain>
					<div class="flex flex-col gap-1">
						<div class="text-secondary text-xs tracking-wide uppercase">Analytic Story</div>
						<h2 class="text-default text-xl leading-tight font-semibold">
							{{ story.name }}
						</h2>
					</div>
				</template>

				<template #default>
					<div class="flex flex-wrap gap-2">
						<Badge v-if="story.date" type="splitted" color="success">
							<template #label>Updated</template>
							<template #value>{{ formatDate(story.date, dFormats.date) }}</template>
						</Badge>
						<Badge v-if="story.authors.length" type="splitted" color="primary">
							<template #label>
								{{ story.authors.length === 1 ? "Author" : "Authors" }}
							</template>
							<template #value>{{ story.authors.join(", ") }}</template>
						</Badge>
						<Badge type="splitted">
							<template #label>Detections</template>
							<template #value>{{ story.detection_count }}</template>
						</Badge>
						<Badge v-if="story.products.length" type="splitted">
							<template #label>
								{{ story.products.length === 1 ? "Product" : "Products" }}
							</template>
							<template #value>{{ story.products.join(", ") }}</template>
						</Badge>
						<Badge v-if="story.version !== null" type="splitted">
							<template #label>Version</template>
							<template #value>v{{ story.version }}</template>
						</Badge>
						<Badge v-if="story.id" type="splitted">
							<template #label>ID</template>
							<template #value>
								{{ story.id }}
							</template>
						</Badge>
					</div>
				</template>
			</CardEntity>

			<!-- Description -->
			<CardEntity>
				<template #headerMain>
					<div class="flex items-center gap-2">
						<Icon name="carbon:document" :size="14" />
						<span class="text-secondary text-xs font-semibold tracking-wide uppercase">Description</span>
					</div>
				</template>
				<template #default>
					{{ story.description }}
				</template>
			</CardEntity>

			<!-- Why it matters -->
			<CardEntity status="warning">
				<template #headerMain>
					<div class="flex items-center gap-2">
						<Icon name="carbon:warning-alt" :size="14" />
						<span class="text-secondary text-xs font-semibold tracking-wide uppercase">Why It Matters</span>
					</div>
				</template>
				<template #default>
					{{ story.why_it_matters }}
				</template>
			</CardEntity>

			<!-- MITRE tactics (if any resolved) -->
			<CardEntity v-if="story.tactics.length">
				<template #headerMain>
					<div class="flex items-center gap-2">
						<Icon name="carbon:flag" :size="14" />
						<span class="text-secondary text-xs font-semibold tracking-wide uppercase">
							MITRE ATT&CK Tactics
						</span>
					</div>
				</template>
				<template #default>
					<div class="flex flex-wrap gap-2">
						<n-tag v-for="t of story.tactics" :key="t" type="warning">
							{{ t.toUpperCase() }}
						</n-tag>
					</div>
				</template>
			</CardEntity>

			<!-- Detections table -->
			<CardEntity>
				<template #header>
					<div class="flex flex-wrap items-center justify-between gap-2">
						<div class="flex items-center gap-2">
							<Icon name="carbon:radar" :size="14" />
							<span class="text-secondary text-xs font-semibold tracking-wide uppercase">Detections</span>
						</div>
						<Badge type="splitted" size="small">
							<template #label>Count</template>
							<template #value>{{ story.detections.length }}</template>
						</Badge>
					</div>
				</template>
				<template #default>
					<n-data-table :columns="detectionColumns" :data="story.detections" size="small" />
				</template>
			</CardEntity>

			<!-- Data sources -->
			<CardEntity>
				<template #headerMain>
					<div class="flex items-center gap-2">
						<Icon name="carbon:data-base" :size="14" />
						<span class="text-secondary text-xs font-semibold tracking-wide uppercase">Data Sources</span>
					</div>
				</template>
				<template #default>
					<div v-if="story.data_sources.length" class="flex flex-wrap gap-2">
						<n-tag v-for="ds of story.data_sources" :key="ds" type="primary">
							{{ ds }}
						</n-tag>
					</div>
					<p v-else class="text-sm">No data sources declared by member detections.</p>
				</template>
			</CardEntity>

			<!-- References -->
			<CardEntity>
				<template #headerMain>
					<div class="flex items-center gap-2">
						<Icon name="carbon:link" :size="14" />
						<span class="text-secondary text-xs font-semibold tracking-wide uppercase">References</span>
					</div>
				</template>
				<template #default>
					<div v-if="story.references.length" class="flex flex-col items-start gap-2">
						<n-button
							v-for="item of story.references"
							:key="item"
							type="primary"
							size="small"
							secondary
							@click="openReference(item)"
						>
							<template #icon>
								<Icon name="carbon:launch" :size="12" />
							</template>
							{{ item }}
						</n-button>
					</div>
					<p v-else class="text-sm">No references provided by member detections.</p>
				</template>
			</CardEntity>
		</div>

		<n-modal
			v-model:show="showRuleModal"
			preset="card"
			:style="{ maxWidth: 'min(820px, 92vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			title="Detection Rule"
			:bordered="false"
			segmented
		>
			<RuleCardContent v-if="modalRuleId" :rule-id="modalRuleId" />
		</n-modal>
	</n-spin>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type { CatalogStoryDetailResponse, CatalogStoryDetection } from "@/types/detection-catalog"
import { NButton, NDataTable, NModal, NSpin, NTag, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import RuleCardContent from "@/components/copilotSearches/RuleCardContent.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{ storyName: string }>()

const emits = defineEmits<{
	(e: "error", message: string): void
}>()

const message = useMessage()
const story = ref<CatalogStoryDetailResponse | null>(null)
const loading = ref(false)
const dFormats = useSettingsStore().dateFormat
const showRuleModal = ref(false)
const modalRuleId = ref<string | null>(null)

function openRuleDetail(ruleId: string) {
	modalRuleId.value = ruleId
	showRuleModal.value = true
}

function openReference(reference: string) {
	window.open(reference, "_blank")
}

function typeBadgeColor(t: string): "error" | "warning" | "primary" | undefined {
	const type = (t || "").toLowerCase()
	if (type === "ttp") return "error"
	if (type === "anomaly") return "warning"
	if (type === "hunting") return "primary"
	return undefined
}

const detectionColumns: DataTableColumns<CatalogStoryDetection> = [
	{
		title: "Name",
		key: "name",
		render: row => (
			<span class="text-primary cursor-pointer underline" onClick={() => openRuleDetail(row.id)}>
				{row.name}
			</span>
		)
	},
	{
		title: "Technique",
		key: "tactics",
		render: row => {
			const ids = row.mitre_attack_id || []
			if (!ids.length && !row.tactics.length) {
				return <span class="text-secondary text-xs">—</span>
			}
			return (
				<div class="flex flex-wrap gap-1">
					{row.tactics.map(t => (
						<NTag key={t} type="warning" size="small">
							{t.toUpperCase()}
						</NTag>
					))}
					{ids.map(id => (
						<NTag key={id} type="info" size="small">
							{id}
						</NTag>
					))}
				</div>
			)
		}
	},
	{
		title: "Type",
		key: "type",
		width: 120,
		render: row => {
			const color = typeBadgeColor(row.type)
			const text = (row.type || "—").toUpperCase()
			return (
				<NTag type={color} size="small" bordered={false}>
					{text}
				</NTag>
			)
		}
	}
]

function load(name: string) {
	loading.value = true
	story.value = null
	Api.detectionCatalog
		.getStory(name)
		.then(res => {
			if (res.data?.success) {
				story.value = res.data
			} else {
				message.warning(res.data?.message || "Failed to load story detail")
			}
		})
		.catch(err => {
			const status = err.response?.status
			let errorMessage = getApiErrorMessage(err) || "Failed to load story detail"
			if (status === 404) {
				errorMessage = `No detections found for story '${name}'`
				message.warning(errorMessage)
			} else {
				message.error(errorMessage)
			}

			emits("error", errorMessage)
		})
		.finally(() => {
			loading.value = false
		})
}

watch(
	() => props.storyName,
	name => load(name)
)
onBeforeMount(() => load(props.storyName))
</script>
