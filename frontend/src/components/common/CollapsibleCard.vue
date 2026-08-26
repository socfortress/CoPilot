<template>
	<div class="border-default flex flex-col overflow-hidden rounded-lg border">
		<div
			class="bg-secondary flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2"
			:class="collapsible && collapsed ? '' : 'border-default border-b'"
		>
			<div class="flex min-w-0 grow flex-wrap items-center gap-x-3 gap-y-2">
				<slot name="header" />
			</div>

			<n-button
				v-if="collapsible"
				text
				class="text-secondary hover:text-primary shrink-0"
				:title="collapsed ? 'Show' : 'Hide'"
				:aria-expanded="!collapsed"
				@click="collapsed = !collapsed"
			>
				<template #icon>
					<Icon :name="ChevronIcon" :size="18" class="chevron" :class="{ 'is-collapsed': collapsed }" />
				</template>
			</n-button>
		</div>

		<!-- v-show, not v-if: collapsing must not throw away a filter the analyst
		     typed, nor re-run the list's rendering when it comes back. -->
		<div v-show="collapsible ? !collapsed : true">
			<slot />
		</div>
	</div>
</template>

<script setup lang="ts">
/**
 * A bordered card with a header band and a body that folds away.
 *
 * The header is a slot, so a caller can put a label, counters and controls in it.
 * Only the chevron toggles — never the header itself — because headers here often
 * carry filter inputs, and a header-wide click target would collapse the card the
 * moment someone clicked into one.
 */
import { NButton } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = withDefaults(
	defineProps<{
		defaultCollapsed?: boolean
		/** false keeps the card shape but drops the chevron — for content meant to stay open. */
		collapsible?: boolean
	}>(),
	{ defaultCollapsed: false, collapsible: true }
)

const ChevronIcon = "carbon:chevron-down"

const collapsed = ref(props.defaultCollapsed)
</script>

<style scoped lang="scss">
.chevron {
	transition: transform 0.2s var(--bezier-ease);

	&.is-collapsed {
		transform: rotate(-90deg);
	}
}
</style>
