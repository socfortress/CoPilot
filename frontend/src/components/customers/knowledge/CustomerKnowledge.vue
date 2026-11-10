<template>
	<div ref="root" class="flex flex-col gap-4" data-testid="customer-knowledge">
		<p class="text-secondary m-0 text-sm" data-testid="knowledge-context-line">{{ CONTEXT_LINE }}</p>

		<transition name="transition-fade-move" mode="out-in">
			<div v-if="formKind" class="flex flex-col gap-4">
				<h4>{{ `${editingFact ? "Edit" : "Add"} ${KIND_WORDS[formKind].noun}` }}</h4>
				<CustomerKnowledgeForm
					:customer-code
					:kind="formKind"
					:editing-fact
					@submitted="onSubmitted"
					@stale="onSubmitted"
					@close="closeForm()"
				/>
			</div>

			<div v-else class="flex flex-col gap-4">
				<CustomerKnowledgeNav v-if="navLinks.length" :links="navLinks" :active @go="go" @ready="refresh()" />

				<n-spin :show="loading">
					<div class="min-h-52">
						<n-alert v-if="failure" type="error" :bordered="false" data-testid="knowledge-failure">
							<div class="flex flex-wrap items-center justify-between gap-3">
								<span>{{ failure }}</span>
								<n-button size="small" @click="load()">Try again</n-button>
							</div>
						</n-alert>

						<template v-else-if="groups">
							<CustomerTabEmpty
								v-if="nothingRecorded"
								icon="carbon:notebook"
								eyebrow="No facts yet"
								title="Nothing recorded about this customer yet"
								description="Facts are what the SOC knows about this customer that an alert can't say: when and where it works, which range is which, what a host is for, what activity to expect."
								:points="EMPTY_POINTS"
								points-title="What you can record"
							>
								<template #actions>
									<n-button
										v-for="group of groups"
										:key="group.kind"
										secondary
										:data-testid="`knowledge-add-${group.kind}`"
										@click="openAdd(group.kind)"
									>
										<template #icon>
											<Icon :name="AddIcon" :size="16" />
										</template>
										Add {{ group.noun }}
									</n-button>
								</template>
							</CustomerTabEmpty>

							<div v-else class="flex flex-col gap-4">
								<n-card
									v-for="group of groups"
									:key="group.kind"
									size="small"
									class="knowledge-anchor"
									:data-knowledge-anchor="group.kind"
									:data-testid="`knowledge-group-${group.kind}`"
								>
									<template #header>
										<div class="flex items-center gap-2">
											<Icon :name="group.icon" :size="16" />
											<span>{{ group.title }}</span>
										</div>
									</template>
									<template #header-extra>
										<n-button
											v-if="group.canAdd"
											size="small"
											:data-testid="`knowledge-add-${group.kind}`"
											@click="openAdd(group.kind)"
										>
											<template #icon>
												<Icon :name="AddIcon" :size="14" />
											</template>
											Add
										</n-button>
									</template>

									<p class="text-secondary mt-0 mb-3 text-sm">{{ group.about }}</p>
									<div v-if="group.facts.length" class="flex flex-col gap-2">
										<CustomerKnowledgeFact
											v-for="fact of group.facts"
											:key="fact.id"
											:fact
											:customer-code
											@edit="openEdit(fact)"
											@deleted="onChanged()"
										/>
									</div>
									<p v-else class="text-tertiary m-0 text-sm" data-testid="knowledge-group-empty">
										No {{ group.title.toLowerCase() }} recorded yet.
									</p>
								</n-card>
							</div>
						</template>
					</div>
				</n-spin>

				<div class="knowledge-anchor" :data-knowledge-anchor="TALON_ANCHOR">
					<CustomerKnowledgeSees :customer-code />
				</div>
			</div>
		</transition>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { KnowledgeItem, KnowledgeKind } from "@/types/customer-knowledge"
import { NAlert, NButton, NCard, NSpin } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CustomerTabEmpty from "../CustomerTabEmpty.vue"
import CustomerKnowledgeFact from "./CustomerKnowledgeFact.vue"
import CustomerKnowledgeForm from "./CustomerKnowledgeForm.vue"
import CustomerKnowledgeNav from "./CustomerKnowledgeNav.vue"
import CustomerKnowledgeSees from "./CustomerKnowledgeSees.vue"
import { CONTEXT_LINE, groupFacts, KIND_WORDS, KINDS } from "./knowledge"
import { useKnowledgeSpy } from "./useKnowledgeSpy"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const emit = defineEmits<{
	/** A fact was saved or deleted, so the count beside this section's name is out of date. */
	(e: "changed"): void
}>()

const AddIcon = "carbon:add-alt"

const EMPTY_POINTS = KINDS.map(kind => ({ title: KIND_WORDS[kind].title, description: KIND_WORDS[kind].about }))

// Null until the first read: a fact list that failed or hasn't arrived isn't an empty one.
const facts = ref<KnowledgeItem[] | null>(null)
const loading = ref(false)
const failure = ref<string | null>(null)
const formKind = ref<KnowledgeKind | null>(null)
const editingFact = ref<KnowledgeItem | null>(null)

const groups = computed(() => (facts.value ? groupFacts(facts.value) : null))
const nothingRecorded = computed(() => !!groups.value?.every(group => !group.facts.length))

const TALON_ANCHOR = "talon"
const root = ref<HTMLElement | null>(null)

// The bar shows only over a list of facts: never over the form, a failure or the empty state.
const navLinks = computed(() => {
	if (formKind.value || failure.value || !groups.value || nothingRecorded.value) return []
	return [
		...groups.value.map(group => ({ id: group.kind, label: group.title, count: group.facts.length })),
		{ id: TALON_ANCHOR, label: "What Talon sees" }
	]
})
const navIds = computed(() => navLinks.value.map(link => link.id))
const { active, go, refresh } = useKnowledgeSpy(root, navIds)

let controller: AbortController | null = null

async function load() {
	controller?.abort()
	const current = new AbortController()
	controller = current
	loading.value = true
	failure.value = null
	try {
		const res = await Api.customerKnowledge.list(customerCode, current.signal)
		if (current.signal.aborted) return
		if (res.data.success) {
			facts.value = res.data.items
		} else {
			failure.value = res.data.message || "Couldn't load this customer's facts"
		}
	} catch (err) {
		if (current.signal.aborted) return
		failure.value = getApiErrorMessage(err as ApiError) || "Couldn't load this customer's facts"
	} finally {
		if (!current.signal.aborted) loading.value = false
	}
}

function openAdd(kind: KnowledgeKind) {
	editingFact.value = null
	formKind.value = kind
}

function openEdit(fact: KnowledgeItem) {
	editingFact.value = fact
	formKind.value = fact.kind
}

function closeForm() {
	formKind.value = null
	editingFact.value = null
}

function onChanged() {
	emit("changed")
	load()
}

function onSubmitted() {
	closeForm()
	onChanged()
}

watch(
	() => customerCode,
	() => {
		closeForm()
		facts.value = null
		load()
	},
	{ immediate: true }
)
onBeforeUnmount(() => controller?.abort())
</script>

<style lang="scss" scoped>
// The bar's backdrop reads the timeline of a marker beside it, not inside it.
[data-testid="customer-knowledge"] {
	timeline-scope: --knowledge-nav-approach;
}

// A jump lands below the app's toolbar and the bar of jumps, not under them.
.knowledge-anchor {
	scroll-margin-top: calc(var(--toolbar-height) + 60px);
}
</style>
