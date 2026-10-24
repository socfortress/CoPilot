<template>
	<!--
		`show` keeps the details mounted while the modal is closed, so an update still in
		flight when the user dismisses it can finish and emit.
	-->
	<n-modal
		v-model:show="show"
		:title
		preset="card"
		display-directive="show"
		class="min-h-135 w-11/12! max-w-200! overflow-hidden"
	>
		<!-- Next to the modal's close button: leave the modal for the entity's own page. -->
		<template #header-extra>
			<n-button
				quaternary
				:focusable="false"
				circle
				size="small"
				:aria-label="pageLabel"
				:title="pageLabel"
				class="opacity-60"
				data-testid="entity-modal-page"
				@click="goToPage()"
			>
				<template #icon>
					<Icon :name="PAGE_ICON" />
				</template>
			</n-button>
		</template>

		<slot :close />
	</n-modal>
</template>

<script setup lang="ts">
import { NButton, NModal } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

/** What a route helper from `useNavigation` returns, e.g. `routeAlertDetails(id)`. */
export interface EntityPageRoute {
	navigate: () => unknown
}

/**
 * One entity (an alert, a case, an agent) in a modal, with a button in its header that opens the
 * entity's own page. EntityDetailsButton opens it from its "View Details"; anything else that names
 * an entity (the Audit log's targets) opens it the same way rather than navigating away.
 */
const { route, entity } = defineProps<{
	/** Modal title, e.g. "Alert Details". */
	title: string
	/** The entity's own page. */
	route: EntityPageRoute
	/** Singular noun used in accessible labels, e.g. "alert". */
	entity: string
}>()

defineSlots<{
	/** The details shown in the modal; `close` hides it (e.g. after a delete). */
	default: (props: { close: () => void }) => unknown
}>()

const show = defineModel<boolean>("show", { default: false })

const PAGE_ICON = "carbon:launch"
const pageLabel = computed(() => `Open ${entity} page`)

function close() {
	show.value = false
}

function goToPage() {
	close()
	route.navigate()
}
</script>
