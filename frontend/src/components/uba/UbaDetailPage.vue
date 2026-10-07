<template>
	<div class="uba-page uba-detail-page @container flex flex-col gap-4" data-testid="uba-detail-page">
		<DetailPageHeader :back-route="routeUba({ customer: customerCode, tab: backTab })" back-label="User Behavior">
			<template #meta>
				<span class="customer-chip flex items-center gap-1.5 font-mono text-xs" data-testid="uba-detail-customer">
					<Icon name="carbon:enterprise" :size="12" />
					{{ customerCode }}
				</span>
			</template>
		</DetailPageHeader>

		<section class="panel border-default rounded-lg border px-5 py-4" data-testid="uba-detail-hero">
			<UbaDrawerHeader :meta :kind="kindLabel" />
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
// One UBA alert or entity as a page of its own: the same header and body as the /uba drawers, under
// a back link to User Behavior (on the matching tab) and the customer it belongs to. Following an
// entity from an alert, or an alert from an entity, opens that one's page, so browser back retraces it.
import type { UbaDrawerMeta } from "./ui/UbaDrawerHeader.vue"
import { computed, ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
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

const { routeUba, routeUbaAlert, routeUbaEntity } = useNavigation()

const meta = ref<UbaDrawerMeta | null>(null)
const kindLabel = computed(() => (kind === "alert" ? "UBA alert" : "Entity"))
const backTab = computed(() => (kind === "alert" ? "alerts" : "entities"))

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

.customer-chip {
	padding: 1px 8px;
	border: 1px solid var(--border-color);
	border-radius: 999px;
	color: var(--fg-secondary-color);
}
</style>
