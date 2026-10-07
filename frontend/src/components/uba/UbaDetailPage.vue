<template>
	<div class="uba-page uba-detail-page @container flex flex-col gap-4" data-testid="uba-detail-page">
		<section class="panel border-default overflow-hidden rounded-lg border" data-testid="uba-detail-hero">
			<!-- Where this page sits: back to User Behavior, the customer, what it is; and a link to share it. -->
			<nav class="bar border-default flex min-h-11 flex-wrap items-center gap-x-2 gap-y-1 border-b px-3 py-1.5" aria-label="UBA">
				<n-button size="small" quaternary @click="goBack(usersBehavior)">
					<template #icon><Icon name="carbon:arrow-left" :size="16" /></template>
					User Behavior
				</n-button>
				<Icon name="carbon:chevron-right" :size="14" class="text-tertiary" aria-hidden="true" />
				<a
					:href="customerPage.href()"
					class="customer-chip flex items-center gap-1.5 font-mono text-xs"
					data-testid="uba-detail-customer"
					@click="follow($event, customerPage)"
				>
					<Icon name="carbon:enterprise" :size="12" />
					{{ customerCode }}
				</a>
				<Icon name="carbon:chevron-right" :size="14" class="text-tertiary" aria-hidden="true" />
				<span class="text-secondary text-sm">{{ kindLabel }}</span>
				<!-- Naive resets a button's margin: the wrapper pushes it to the end. -->
				<span class="ml-auto">
					<n-button
						size="small"
						quaternary
						data-testid="uba-detail-copy-link"
						@click="copyLink"
					>
						<template #icon><Icon :name="copied ? 'carbon:checkmark' : 'carbon:link'" :size="15" /></template>
						Copy link
					</n-button>
				</span>
			</nav>
			<div class="px-5 py-4">
				<UbaDrawerHeader :meta :kind="kindLabel" />
			</div>
		</section>

		<section class="panel border-default rounded-lg border px-5 pt-5 pb-8">
			<UbaAlertDetail
				v-if="kind === 'alert'"
				:key="`alert:${customerCode}:${id}`"
				:customer-code
				:alert-id="id"
				@open-entity="key => routeUbaEntity(customerCode, key).navigate()"
				@meta="m => (meta = m)"
			/>
			<UbaEntityDetail
				v-else
				:key="`entity:${customerCode}:${id}`"
				:customer-code
				:entity-key="id"
				@open-alert="alertId => routeUbaAlert(customerCode, alertId).navigate()"
				@meta="m => (meta = m)"
			/>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { UbaDrawerMeta } from "./ui/UbaDrawerHeader.vue"
// One UBA alert or entity as a page of its own: the same header and body as the /uba drawers. Above the
// header, a bar says where it sits (back to User Behavior on the matching tab, the customer's view)
// and copies a link to it. Following an entity from an alert, or an alert from an entity, opens that
// one's page, so browser back retraces it.
import type { EntityRoute } from "@/composables/useNavigation"
import { useClipboard } from "@vueuse/core"
import { NButton, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import UbaAlertDetail from "./UbaAlertDetail.vue"
import UbaEntityDetail from "./UbaEntityDetail.vue"
import UbaDrawerHeader from "./ui/UbaDrawerHeader.vue"
import "./uba-shared.css"

const { customerCode, kind, id } = defineProps<{
	customerCode: string
	kind: "alert" | "entity"
	/** The UBA alert id, or the entity key. */
	id: string
}>()

const { routeUba, routeUbaAlert, routeUbaEntity, goBack } = useNavigation()
const message = useMessage()
const { copy, copied } = useClipboard({ legacy: true })

const meta = ref<UbaDrawerMeta | null>(null)
const kindLabel = computed(() => (kind === "alert" ? "UBA alert" : "Entity"))
/** Where "User Behavior" lands on a cold load: the customer, on the tab that lists this kind. */
const usersBehavior = computed(() => routeUba({ customer: customerCode, tab: kind === "alert" ? "alerts" : "entities" }))
const customerPage = computed(() => routeUba({ customer: customerCode }))
const thisPage = computed(() => (kind === "alert" ? routeUbaAlert(customerCode, id) : routeUbaEntity(customerCode, id)))

function follow(event: MouseEvent, page: EntityRoute) {
	// Leave a modified click (new tab / window) to the browser.
	if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
	event.preventDefault()
	page.navigate()
}

async function copyLink() {
	await copy(thisPage.value.fullUrl())
	message.success("Link copied")
}

// A new alert or entity: its header comes from the new body, not the previous one.
watch(
	() => `${kind}:${customerCode}:${id}`,
	() => {
		meta.value = null
	}
)
</script>

<style scoped>
.panel {
	background-color: var(--bg-default-color);
}

.bar {
	background-color: var(--bg-secondary-color);
}

.customer-chip {
	height: 22px;
	padding: 0 8px;
	border: 1px solid var(--border-color);
	border-radius: 999px;
	color: var(--fg-secondary-color);
	text-decoration: none;
	transition:
		color 0.2s,
		border-color 0.2s;
}

.customer-chip:hover {
	color: var(--primary-color);
	border-color: rgb(var(--primary-color-rgb) / 0.5);
}
</style>
