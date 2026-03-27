<template>
	<n-card content-class="p-0!" :hoverable="clickable" :class="{ 'group cursor-pointer': clickable }" size="small">
		<div
			class="card-header border-border flex items-center justify-between gap-4 overflow-hidden border-b px-4 py-3"
			:class="{ 'group-hover:text-primary': clickable }"
		>
			<div class="truncate text-base">{{ title }}</div>
			<Icon v-if="clickable" :name="icon || 'carbon:arrow-up-right'" />
			<slot name="header-extra" />
		</div>

		<div class="card-content divide-border grid grow grid-cols-[repeat(auto-fit,minmax(0,1fr))] divide-x">
			<div
				v-for="item of values"
				:key="JSON.stringify(item)"
				class="value-box flex flex-col"
				:class="item.status"
			>
				<div class="value flex grow items-center justify-center">
					{{ item.value }}
				</div>
				<div
					v-if="item.label"
					class="label"
					:class="{ 'hover:text-primary! cursor-pointer transition-colors': selectable }"
					@click="emit('select', item)"
				>
					{{ item.label }}
					<Icon v-if="selectable" :name="icon || 'carbon:arrow-up-right'" />
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

export interface ItemProps {
	value: number | string
	label?: string
	status?: "success" | "warning" | "error"
}

defineProps<{
	title: string
	values: ItemProps[]
	clickable?: boolean
	icon?: string
	selectable?: boolean
}>()

const emit = defineEmits<{
	select: [item: ItemProps]
}>()
</script>

<style scoped lang="scss">
.n-card {
	overflow: hidden;

	.card-content {
		.value-box {
			text-align: center;
			overflow: hidden;

			.value {
				font-family: var(--font-family-display);
				padding: 10px 6px;
				font-size: 22px;
				text-overflow: ellipsis;
				white-space: nowrap;
				overflow: hidden;
				font-weight: bold;
				text-overflow: ellipsis;
				white-space: nowrap;
				line-height: 1;
				overflow: hidden;
			}

			.label {
				font-family: var(--font-family-mono);
				border-top: 1px solid var(--border-color);
				color: var(--fg-secondary-color);
				font-size: 13px;
				padding: 6px;
				line-height: 1;
				background-color: var(--bg-secondary-color);
				text-overflow: ellipsis;
				white-space: nowrap;
				overflow: hidden;
				text-transform: uppercase;
				display: flex;
				align-items: center;
				justify-content: center;
				gap: 4px;
			}

			&.success {
				.value {
					color: var(--success-color);
				}
				.label {
					color: var(--success-color);
				}
			}

			&.warning {
				.value {
					color: var(--warning-color);
				}
				.label {
					color: var(--warning-color);
				}
			}

			&.error {
				.value {
					color: var(--error-color);
				}
				.label {
					color: var(--error-color);
				}
			}
		}
	}

	&.hovered {
		&:hover {
			border-color: var(--primary-color);
		}
	}
}
</style>
