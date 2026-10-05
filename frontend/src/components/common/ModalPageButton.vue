<template>
	<n-tooltip v-if="route && !alreadyThere" placement="bottom">
		<template #trigger>
			<n-button
				tag="a"
				:href="route.href()"
				quaternary
				circle
				:focusable="false"
				size="small"
				class="modal-page-button opacity-60"
				:aria-label="label"
				data-testid="modal-page-button"
				@click="go"
			>
				<template #icon><Icon name="carbon:launch" :size="16" /></template>
			</n-button>
		</template>
		{{ label }}
	</n-tooltip>
</template>

<script setup lang="ts">
// The "open this as a page" button of an entity modal: put it in the modal's
// `#header-extra` slot and it sits next to the close button. A real link, so a
// middle-click or "open in new tab" works; a plain click navigates and tells the
// parent to close the modal (a modal owned by something that outlives the page —
// the layout, the search palette — would otherwise stay open on top of it). Hidden
// when the page it points to is the one already open.
import type { EntityRoute } from "@/composables/useNavigation"
import { NButton, NTooltip } from "naive-ui"
import { computed } from "vue"
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"

const { route, label = "Open the page" } = defineProps<{
	/** The entity's page, from a `useNavigation().route*()` helper; nothing renders without one. */
	route?: EntityRoute | null
	label?: string
}>()

const emit = defineEmits<{ (e: "navigate"): void }>()

const router = useRouter()

const alreadyThere = computed(() => !!route && router.currentRoute.value.fullPath === route.href())

function go(event: MouseEvent) {
	// Let the browser handle a modified click (new tab / window) on the link itself.
	if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
	event.preventDefault()
	emit("navigate")
	route?.navigate()
}
</script>
