<template>
	<div class="story-detail flex flex-col gap-6">
		<!-- Back nav + header. Uses RouterLink directly (custom slot) so the
		     navigation is Vue Router-native — no interception, no race, no
		     ambiguity. Always lands on /detection-catalog with no query. -->
		<div class="flex flex-col gap-4">
			<div>
				<RouterLink
					:to="{ name: 'DetectionCatalog', query: {} }"
					custom
					v-slot="{ navigate }"
				>
					<n-button size="small" quaternary @click="navigate">
						<template #icon><Icon name="carbon:arrow-left" /></template>
						All Stories
					</n-button>
				</RouterLink>
			</div>

			<n-spin :show="loading">
				<template v-if="story">
					<div class="flex flex-col gap-4">
						<h2 class="m-0">Analytics Story: {{ story.name }}</h2>

						<div class="flex flex-wrap gap-2">
							<Badge v-if="story.date" type="splitted" color="success">
								<template #label>Date</template>
								<template #value>{{ story.date }}</template>
							</Badge>
							<Badge v-if="story.id" type="splitted">
								<template #label>ID</template>
								<template #value>
									<code>{{ story.id }}</code>
								</template>
							</Badge>
							<Badge v-if="story.authors.length" type="splitted" color="primary">
								<template #label>Author{{ story.authors.length === 1 ? "" : "s" }}</template>
								<template #value>{{ story.authors.join(", ") }}</template>
							</Badge>
							<Badge v-if="story.products.length" type="splitted">
								<template #label>Product{{ story.products.length === 1 ? "" : "s" }}</template>
								<template #value>{{ story.products.join(", ") }}</template>
							</Badge>
							<Badge v-if="story.version !== null" type="splitted">
								<template #label>Version</template>
								<template #value>v{{ story.version }}</template>
							</Badge>
						</div>
					</div>
				</template>
			</n-spin>
		</div>

		<template v-if="story">
			<!-- Full-width content. TOC sidebar removed; sections flow vertically
			     and the page is short enough that scrolling is fine. -->
			<div class="flex flex-col gap-8">
				<section>
					<h3>Description</h3>
					<p class="text-secondary">{{ story.description }}</p>
				</section>

				<section>
					<h3>Why it matters</h3>
					<p class="text-secondary">{{ story.why_it_matters }}</p>
				</section>

				<section>
					<h3>Detections</h3>
					<n-data-table
						:columns="detectionColumns"
						:data="story.detections"
						size="small"
						:bordered="true"
					/>
				</section>

				<section>
					<h3>Data Sources</h3>
					<div v-if="story.data_sources.length" class="flex flex-wrap gap-2">
						<n-tag v-for="ds of story.data_sources" :key="ds" size="small" type="info">
							{{ ds }}
						</n-tag>
					</div>
					<p v-else class="text-tertiary text-sm">No data sources declared by member detections.</p>
				</section>

				<section>
					<h3>References</h3>
					<ul v-if="story.references.length" class="reference-list">
						<li v-for="ref of story.references" :key="ref">
							<a :href="ref" target="_blank" rel="noopener">{{ ref }}</a>
						</li>
					</ul>
					<p v-else class="text-tertiary text-sm">No references provided by member detections.</p>
				</section>
			</div>
		</template>

		<!-- Rule detail modal — opened when an analyst clicks a row in the
		     Detections table. Reuses the existing CoPilot Searches rule
		     content component so the modal looks identical to what they see
		     elsewhere. -->
		<n-modal
			v-model:show="showRuleModal"
			preset="card"
			:style="{ maxWidth: 'min(750px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
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
import { NButton, NDataTable, NModal, NSpin, NTag, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import RuleCardContent from "@/components/copilotSearches/RuleCardContent.vue"

const props = defineProps<{ storyName: string }>()
// Emit kept for shell compat (it listens for `back` to clear state), but
// the actual navigation is the router.push below — parent's watcher on
// route.query.story is what actually drives the v-if back to the index.
const emit = defineEmits<{ (e: "back"): void }>()

const router = useRouter()
const message = useMessage()
const story = ref<CatalogStoryDetailResponse | null>(null)
const loading = ref(false)

const showRuleModal = ref(false)
const modalRuleId = ref<string | null>(null)

function goBack() {
	// Canonical reset to the catalog index. By name + no query, so there's
	// zero ambiguity about destination. Parent's watcher on
	// route.query.story will null out openStoryName when the param goes
	// away, which flips the v-if back to the index view.
	router.push({ name: "DetectionCatalog" })
}

function openRuleDetail(ruleId: string) {
	modalRuleId.value = ruleId
	showRuleModal.value = true
}

function typeBadge(t: string) {
	const type = (t || "").toLowerCase()
	if (type === "ttp") return "danger"
	if (type === "anomaly") return "warning"
	if (type === "hunting") return "info"
	return undefined
}

const detectionColumns: DataTableColumns<CatalogStoryDetection> = [
	{
		title: "Name",
		key: "name",
		render: row => (
			<a
				class="text-primary cursor-pointer hover:underline"
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
				return <em class="text-tertiary">—</em>
			}
			return (
				<div class="flex flex-wrap gap-1">
					{row.tactics.map(t => (
						<NTag key={t} size="tiny" bordered={false} type="info">{t}</NTag>
					))}
					{ids.map(id => (
						<NTag key={id} size="tiny" bordered={false}>{id}</NTag>
					))}
				</div>
			)
		}
	},
	{
		title: "Type",
		key: "type",
		width: 110,
		render: row => (
			<NTag size="small" bordered={false} type={typeBadge(row.type) as any}>
				{(row.type || "—").toUpperCase()}
			</NTag>
		)
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
.reference-list {
	display: flex;
	flex-direction: column;
	gap: 4px;
	padding-left: 20px;
	list-style: disc;
}
.reference-list a {
	color: var(--primary-color);
	word-break: break-all;
}
.reference-list a:hover {
	text-decoration: underline;
}

section h3 {
	margin: 0 0 8px 0;
	font-size: 1.05rem;
}
</style>
