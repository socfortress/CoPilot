<template>
	<div class="border-default flex flex-col overflow-hidden rounded-lg border">
		<div
			class="bg-secondary flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2"
			:class="collapsed ? '' : 'border-default border-b'"
		>
			<div class="flex min-w-0 grow flex-wrap items-center gap-x-3 gap-y-2">
				<slot name="header" />
			</div>

			<!-- Only the chevron toggles, not the whole header: these headers carry
			     filter inputs, and a header-wide click target would collapse the card
			     the moment someone clicked into one. -->
			<n-button
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
		<div v-show="!collapsed">
			<slot />
		</div>
	</div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import { ref } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = withDefaults(defineProps<{ defaultCollapsed?: boolean }>(), { defaultCollapsed: false })

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
