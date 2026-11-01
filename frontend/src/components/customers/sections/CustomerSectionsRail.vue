<template>
	<nav class="customer-sections-rail" :aria-label="`${group.label} sections`" data-testid="customer-sections-rail">
		<div class="rail-list">
			<template v-for="subgroup of group.subgroups" :key="subgroup.label">
				<button
					v-if="subgroup.label"
					type="button"
					class="rail-subgroup"
					:aria-expanded="!isCollapsed(subgroup.label)"
					:data-testid="`rail-subgroup-${subgroup.label}`"
					@click="toggle(subgroup.label)"
				>
					<Icon
						:name="isCollapsed(subgroup.label) ? 'carbon:chevron-right' : 'carbon:chevron-down'"
						:size="12"
					/>
					<span class="min-w-0 flex-1 truncate text-left">{{ subgroup.label }}</span>
					<span v-if="summaryOf(subgroup.sections)" class="rail-summary">
						{{ summaryOf(subgroup.sections) }}
					</span>
				</button>
				<template v-if="!isCollapsed(subgroup.label)">
					<button
						v-for="section of subgroup.sections"
						:key="section.id"
						type="button"
						class="rail-item"
						:class="{ 'is-current': section.id === current, 'is-nested': !!subgroup.label }"
						:aria-current="section.id === current ? 'page' : undefined"
						:data-testid="`rail-item-${section.id}`"
						@click="emit('select', section.id)"
					>
						<SectionMark v-if="sectionState(section, status)?.kind === 'switch'" :state="sectionState(section, status)" />
						<span class="min-w-0 flex-1 truncate text-left">{{ section.label }}</span>
						<SectionMark
							v-if="sectionState(section, status)?.kind === 'count'"
							:state="sectionState(section, status)"
						/>
					</button>
				</template>
			</template>
		</div>

		<button type="button" class="rail-hide" data-testid="rail-hide" @click="emit('hide')">
			<Icon name="carbon:side-panel-close" :size="14" />
			Hide sections
		</button>
	</nav>
</template>

<script setup lang="ts">
import type { GroupView, SectionDef, SectionId } from "./sections"
import type { CustomerSectionStatus } from "@/types/customers"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import SectionMark from "./SectionMark.vue"
import { sectionById, sectionState, switchSummary } from "./sections"

/**
 * The open group's sections (#1325), in subgroups that fold away. A switch's light sits before
 * its name, a list's count after it. The subgroup holding the current section is always open.
 */
const { group, current, status } = defineProps<{
	group: GroupView
	current: SectionId
	status: CustomerSectionStatus | null
}>()

const emit = defineEmits<{
	(e: "select", id: SectionId): void
	(e: "hide"): void
}>()

const collapsed = ref(new Set<string>())

function key(label: string) {
	return `${group.id}/${label}`
}

function isCollapsed(label: string): boolean {
	return collapsed.value.has(key(label))
}

function toggle(label: string) {
	const next = new Set(collapsed.value)
	if (next.has(key(label))) next.delete(key(label))
	else next.add(key(label))
	collapsed.value = next
}

function summaryOf(sections: SectionDef[]): string | null {
	return switchSummary(sections, status)
}

watch(
	() => current,
	id => {
		const label = sectionById(id).subgroup
		if (label && isCollapsed(label)) toggle(label)
	},
	{ immediate: true }
)
</script>

<style lang="scss" scoped>
.customer-sections-rail {
	display: flex;
	flex-direction: column;
	width: 240px;
	flex-shrink: 0;
	padding: 12px 0;
	background-color: var(--bg-secondary-color);
	border-right: 1px solid var(--border-color);

	.rail-list {
		display: flex;
		flex: 1;
		flex-direction: column;
		gap: 1px;
	}

	.rail-subgroup {
		display: flex;
		align-items: center;
		gap: 8px;
		height: 30px;
		margin-top: 6px;
		padding: 0 14px;
		font-family: var(--font-family-mono);
		font-size: 11px;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--fg-secondary-color);

		&:first-child {
			margin-top: 0;
		}
	}

	.rail-summary {
		letter-spacing: 0;
		text-transform: none;
	}

	.rail-item {
		position: relative;
		display: flex;
		align-items: center;
		gap: 10px;
		height: 34px;
		padding: 0 14px 0 16px;
		font-size: 14px;
		color: var(--fg-default-color);

		&.is-nested {
			padding-left: 34px;
		}

		&:hover {
			background-color: var(--hover-color);
		}

		&.is-current {
			color: var(--primary-color);
			background-color: rgba(var(--primary-color-rgb), 0.08);

			&::after {
				content: "";
				position: absolute;
				right: -1px;
				top: 0;
				bottom: 0;
				width: 2px;
				background-color: var(--primary-color);
			}
		}
	}

	.rail-hide {
		display: flex;
		align-items: center;
		gap: 8px;
		width: fit-content;
		height: 30px;
		margin: 16px 12px 0;
		padding: 0 10px;
		border: 1px solid var(--border-color);
		border-radius: var(--border-radius-small);
		font-size: 12px;
		color: var(--fg-secondary-color);

		&:hover {
			color: var(--fg-default-color);
		}
	}

	button:focus-visible {
		outline: 2px solid var(--primary-color);
		outline-offset: -2px;
	}

	@container customer-sections (max-width: 700px) {
		width: 100%;
		padding: 6px 8px;
		border-right: 0;
		border-bottom: 1px solid var(--border-color);

		.rail-list {
			flex-direction: row;
			overflow-x: auto;
			scrollbar-width: none;
		}

		.rail-subgroup,
		.rail-hide {
			display: none;
		}

		.rail-item,
		.rail-item.is-nested {
			flex-shrink: 0;
			padding: 0 10px;
			border-radius: var(--border-radius-small);

			&.is-current::after {
				display: none;
			}
		}
	}
}
</style>
