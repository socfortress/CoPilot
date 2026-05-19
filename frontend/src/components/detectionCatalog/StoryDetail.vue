<template>
	<div class="story-detail flex flex-col gap-6">
		<!-- Back nav. RouterLink with custom slot so navigation is router-
		     native — no event interception or race conditions. The parent's
		     watcher on route.query.story drives the v-if back to the index. -->
		<div>
			<RouterLink :to="{ name: 'DetectionCatalog', query: {} }" custom v-slot="{ navigate }">
				<n-button size="small" quaternary @click="navigate">
					<template #icon><Icon name="carbon:arrow-left" /></template>
					Back to Detections Catalog
				</n-button>
			</RouterLink>
		</div>

		<n-spin :show="loading">
			<template v-if="story">
				<!-- HERO ----------------------------------------------------
				     Story title + key metadata badges. CardEntity gives the
				     section CoPilot's standard card chrome. -->
				<CardEntity size="medium">
					<template #headerMain>
						<div class="flex items-center gap-3">
							<div class="story-hero-icon">
								<Icon name="carbon:book" :size="20" />
							</div>
							<div class="flex flex-col gap-1">
								<div class="text-tertiary text-xs uppercase tracking-wide">
									Analytic Story
								</div>
								<h2 class="m-0 text-2xl font-semibold leading-tight">
									{{ story.name }}
								</h2>
							</div>
						</div>
					</template>

					<template #default>
						<div class="flex flex-wrap gap-2">
							<Badge v-if="story.date" type="splitted" color="success">
								<template #label>Updated</template>
								<template #value>{{ story.date }}</template>
							</Badge>
							<Badge type="splitted">
								<template #label>Detections</template>
								<template #value>{{ story.detection_count }}</template>
							</Badge>
							<Badge v-if="story.authors.length" type="splitted" color="primary">
								<template #label>
									{{ story.authors.length === 1 ? "Author" : "Authors" }}
								</template>
								<template #value>{{ story.authors.join(", ") }}</template>
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
								<template #value><code>{{ story.id }}</code></template>
							</Badge>
						</div>
					</template>
				</CardEntity>
			</template>
		</n-spin>

		<template v-if="story">
			<!-- Description -->
			<CardEntity size="medium">
				<template #headerMain>
					<div class="flex items-center gap-2">
						<Icon name="carbon:document" :size="14" />
						<span class="text-sm font-semibold uppercase tracking-wide">Description</span>
					</div>
				</template>
				<template #default>
					<p class="text-secondary m-0 leading-relaxed">{{ story.description }}</p>
				</template>
			</CardEntity>

			<!-- Why it matters -->
			<CardEntity size="medium" status="warning">
				<template #headerMain>
					<div class="flex items-center gap-2">
						<Icon name="carbon:warning-alt" :size="14" />
						<span class="text-sm font-semibold uppercase tracking-wide">Why It Matters</span>
					</div>
				</template>
				<template #default>
					<p class="text-secondary m-0 leading-relaxed">{{ story.why_it_matters }}</p>
				</template>
			</CardEntity>

			<!-- MITRE tactics (if any resolved) -->
			<CardEntity v-if="story.tactics.length" size="medium">
				<template #headerMain>
					<div class="flex items-center gap-2">
						<Icon name="carbon:flag" :size="14" />
						<span class="text-sm font-semibold uppercase tracking-wide">
							MITRE ATT&CK Tactics
						</span>
					</div>
				</template>
				<template #default>
					<div class="flex flex-wrap gap-2">
						<span v-for="t of story.tactics" :key="t" class="tactic-pill">
							{{ t.toUpperCase() }}
						</span>
					</div>
				</template>
			</CardEntity>

			<!-- Detections table -->
			<CardEntity size="medium">
				<template #header>
					<div class="flex flex-wrap items-center justify-between gap-2">
						<div class="flex items-center gap-2">
							<Icon name="carbon:radar" :size="14" />
							<span class="text-sm font-semibold uppercase tracking-wide">Detections</span>
						</div>
						<Badge type="splitted" color="primary">
							<template #label>Count</template>
							<template #value>{{ story.detections.length }}</template>
						</Badge>
					</div>
				</template>
				<template #default>
					<n-data-table
						:columns="detectionColumns"
						:data="story.detections"
						size="small"
						class="catalog-table"
					/>
				</template>
			</CardEntity>

			<!-- Data sources -->
			<CardEntity size="medium">
				<template #headerMain>
					<div class="flex items-center gap-2">
						<Icon name="carbon:data-base" :size="14" />
						<span class="text-sm font-semibold uppercase tracking-wide">Data Sources</span>
					</div>
				</template>
				<template #default>
					<div v-if="story.data_sources.length" class="flex flex-wrap gap-2">
						<span v-for="ds of story.data_sources" :key="ds" class="data-source-pill">
							{{ ds }}
						</span>
					</div>
					<p v-else class="text-tertiary m-0 text-sm">
						No data sources declared by member detections.
					</p>
				</template>
			</CardEntity>

			<!-- References -->
			<CardEntity size="medium">
				<template #headerMain>
					<div class="flex items-center gap-2">
						<Icon name="carbon:link" :size="14" />
						<span class="text-sm font-semibold uppercase tracking-wide">References</span>
					</div>
				</template>
				<template #default>
					<ul v-if="story.references.length" class="reference-list">
						<li v-for="ref of story.references" :key="ref">
							<a :href="ref" target="_blank" rel="noopener">
								<Icon name="carbon:launch" :size="12" />
								<span>{{ ref }}</span>
							</a>
						</li>
					</ul>
					<p v-else class="text-tertiary m-0 text-sm">
						No references provided by member detections.
					</p>
				</template>
			</CardEntity>
		</template>

		<!-- Rule detail modal — reuses the same CoPilot Searches RuleCardContent
		     so the modal looks identical to what analysts see in the original
		     CoPilot Searches page. -->
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
	</div>
</template>

<script setup lang="tsx">
import type { DataTableColumns } from "naive-ui"
import type {
	CatalogStoryDetailResponse,
	CatalogStoryDetection
} from "@/types/detectionCatalog.d"
import { NButton, NDataTable, NModal, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import RuleCardContent from "@/components/copilotSearches/RuleCardContent.vue"

const props = defineProps<{ storyName: string }>()
// `back` emit kept for shell compat — parent listens to also reset state.
// Real navigation is the RouterLink in the template.
const emit = defineEmits<{ (e: "back"): void }>()

const router = useRouter()
const message = useMessage()
const story = ref<CatalogStoryDetailResponse | null>(null)
const loading = ref(false)

const showRuleModal = ref(false)
const modalRuleId = ref<string | null>(null)

function openRuleDetail(ruleId: string) {
	modalRuleId.value = ruleId
	showRuleModal.value = true
}

function typeBadgeColor(t: string): "danger" | "warning" | "primary" | undefined {
	const type = (t || "").toLowerCase()
	if (type === "ttp") return "danger"
	if (type === "anomaly") return "warning"
	if (type === "hunting") return "primary"
	return undefined
}

const detectionColumns: DataTableColumns<CatalogStoryDetection> = [
	{
		title: "Name",
		key: "name",
		render: row => (
			<a
				class="detection-name-link"
				onClick={() => openRuleDetail(row.id)}
			>
				{row.name}
			</a>
		)
	},
	{
		title: "Technique",
		key: "tactics",
		render: row => {
			const ids = row.mitre_attack_id || []
			if (!ids.length && !row.tactics.length) {
				return <span class="text-tertiary text-xs">—</span>
			}
			return (
				<div class="flex flex-wrap gap-1">
					{row.tactics.map(t => (
						<span key={t} class="chip chip-tactic">{t.toUpperCase()}</span>
					))}
					{ids.map(id => (
						<span key={id} class="chip chip-mitre">{id}</span>
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
			return <span class={`type-pill type-${color ?? "default"}`}>{text}</span>
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
			if (status === 404) {
				message.warning(`No detections found for story '${name}'`)
			} else {
				message.error(err.response?.data?.detail || err.response?.data?.message || "Failed to load story detail")
			}
		})
		.finally(() => {
			loading.value = false
		})
}

watch(() => props.storyName, name => load(name))
onBeforeMount(() => load(props.storyName))
</script>

<style scoped lang="scss">
.story-detail {
	.story-hero-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 44px;
		height: 44px;
		border-radius: 10px;
		background-color: rgba(var(--primary-color-rgb) / 0.1);
		color: var(--primary-color);
		flex-shrink: 0;
	}

	.tactic-pill {
		display: inline-flex;
		align-items: center;
		padding: 4px 12px;
		font-size: 0.75rem;
		font-weight: 600;
		letter-spacing: 0.05em;
		border-radius: 999px;
		color: var(--warning-color);
		background-color: rgba(var(--warning-color-rgb) / 0.1);
		border: 1px solid rgba(var(--warning-color-rgb) / 0.25);
	}

	.data-source-pill {
		display: inline-flex;
		align-items: center;
		padding: 4px 12px;
		font-size: 0.78rem;
		font-weight: 500;
		border-radius: 999px;
		color: var(--primary-color);
		background-color: rgba(var(--primary-color-rgb) / 0.08);
		border: 1px solid rgba(var(--primary-color-rgb) / 0.2);
	}

	.reference-list {
		display: flex;
		flex-direction: column;
		gap: 6px;
		margin: 0;
		padding: 0;
		list-style: none;

		li a {
			display: inline-flex;
			align-items: center;
			gap: 8px;
			color: var(--primary-color);
			text-decoration: none;
			font-size: 0.85rem;
			padding: 6px 10px;
			border-radius: 6px;
			background-color: rgba(var(--primary-color-rgb) / 0.04);
			border: 1px solid transparent;
			transition: all 0.15s var(--bezier-ease);
			word-break: break-all;

			&:hover {
				background-color: rgba(var(--primary-color-rgb) / 0.1);
				border-color: rgba(var(--primary-color-rgb) / 0.2);
			}
		}
	}
}

/* Detection-name link inside the detections table — clearly clickable
   without being a loud button. */
:deep(.detection-name-link) {
	color: var(--primary-color);
	font-weight: 500;
	cursor: pointer;
	transition: color 0.15s var(--bezier-ease);

	&:hover {
		text-decoration: underline;
	}
}

/* Catalog table styling — same rules as StoriesIndex so detail tables match
   the index ones visually. */
.catalog-table :deep(.n-data-table-th) {
	background-color: var(--bg-secondary-color);
	font-weight: 600;
	font-size: 12px;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	color: var(--fg-secondary-color);
}
.catalog-table :deep(.n-data-table-tr) {
	transition: background-color 0.15s var(--bezier-ease);
}
.catalog-table :deep(.n-data-table-tr:hover) {
	background-color: rgba(var(--primary-color-rgb) / 0.04);
}
.catalog-table :deep(.n-data-table-td) {
	padding: 10px 12px;
}

:deep(.chip) {
	display: inline-flex;
	align-items: center;
	padding: 2px 8px;
	font-size: 0.72rem;
	font-weight: 500;
	line-height: 1.4;
	border-radius: 6px;
	border: 1px solid transparent;
	white-space: nowrap;
}
:deep(.chip-tactic) {
	color: var(--warning-color);
	background-color: rgba(var(--warning-color-rgb) / 0.08);
	border-color: rgba(var(--warning-color-rgb) / 0.2);
	font-weight: 600;
	letter-spacing: 0.04em;
}
:deep(.chip-mitre) {
	color: var(--fg-default-color);
	background-color: var(--bg-secondary-color);
	border-color: var(--border-color);
	font-family: var(--font-family-mono);
}
:deep(.chip-product) {
	color: var(--fg-default-color);
	background-color: var(--bg-secondary-color);
	border-color: var(--border-color);
}

/* Type pills for detection rows — color-coded by rule type (TTP/anomaly/
   hunting) so analysts can spot the type at a glance without reading. */
:deep(.type-pill) {
	display: inline-flex;
	align-items: center;
	padding: 3px 10px;
	font-size: 0.7rem;
	font-weight: 600;
	letter-spacing: 0.04em;
	border-radius: 999px;
	border: 1px solid transparent;
}
:deep(.type-pill.type-default) {
	color: var(--fg-secondary-color);
	background-color: var(--bg-secondary-color);
	border-color: var(--border-color);
}
:deep(.type-pill.type-danger) {
	color: var(--error-color);
	background-color: rgba(var(--error-color-rgb) / 0.08);
	border-color: rgba(var(--error-color-rgb) / 0.25);
}
:deep(.type-pill.type-warning) {
	color: var(--warning-color);
	background-color: rgba(var(--warning-color-rgb) / 0.1);
	border-color: rgba(var(--warning-color-rgb) / 0.25);
}
:deep(.type-pill.type-primary) {
	color: var(--primary-color);
	background-color: rgba(var(--primary-color-rgb) / 0.08);
	border-color: rgba(var(--primary-color-rgb) / 0.2);
}
</style>
