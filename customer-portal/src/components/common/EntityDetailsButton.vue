<template>
	<div>
		<n-button-group :size>
			<n-button :focusable="false" :ghost @click="open()">
				<template #icon>
					<Icon name="carbon:view" />
				</template>
				{{ label ?? $t("common.entityDetails.viewDetails") }}
			</n-button>
			<n-button :focusable="false" :ghost :aria-label="pageLabel" :title="pageLabel" @click="goToPage()">
				<template #icon>
					<Icon :name="PAGE_ICON" />
				</template>
			</n-button>
		</n-button-group>

		<EntityDetailsModal v-model:show="showDetails" :title :route :entity>
			<slot :close />
		</EntityDetailsModal>
	</div>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { EntityPageRoute } from "./EntityDetailsModal.vue"
import { NButton, NButtonGroup } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import EntityDetailsModal from "./EntityDetailsModal.vue"
import { entityPageLabel } from "./entityPageLabel"

/**
 * The "View Details" + "open page" pair used for alerts, cases and agents: the first
 * shows the entity in a modal, the second (also in the modal header) opens its page.
 * Wrappers such as AlertDetailsButton choose the details component and the route.
 */
const { route, entity, label } = defineProps<{
	/** Modal title, e.g. "Alert Details". */
	title: string
	/** The entity's own page. */
	route: EntityPageRoute
	/** Singular noun used in accessible labels, e.g. "alert". */
	entity: string
	/** The button's text; "View Details" when left out. */
	label?: string
	size?: ButtonSize
	/** Transparent background, for buttons sitting on a surface that already has one. */
	ghost?: boolean
}>()

defineSlots<{
	/** The details shown in the modal; `close` hides it (e.g. after a delete). */
	default: (props: { close: () => void }) => unknown
}>()

const PAGE_ICON = "carbon:launch"

const showDetails = ref(false)
const pageLabel = computed(() => entityPageLabel(entity))

function open() {
	showDetails.value = true
}

function close() {
	showDetails.value = false
}

function goToPage() {
	close()
	route.navigate()
}

defineExpose({ open, close })
</script>
