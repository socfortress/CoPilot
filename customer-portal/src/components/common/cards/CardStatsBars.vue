<template>
	<n-card content-class="p-0!" :hoverable="clickable" :class="{ 'group cursor-pointer': clickable }" size="small">
		<div
			class="card-header border-border flex items-center justify-between gap-4 overflow-hidden border-b px-4 py-3"
			:class="{ 'group-hover:text-primary transition-colors': clickable }"
		>
			<div class="truncate text-base">{{ title }}</div>
			<Icon v-if="clickable" :name="icon || 'carbon:arrow-up-right'" />
		</div>

		<div class="card-content flex flex-col gap-3">
			<div v-if="barValues.length" class="bars flex">
				<div
					v-for="item of barValues"
					:key="JSON.stringify(item)"
					:class="item.status"
					class="bar"
					:style="{ width: `${item.percentage}%` }"
				>
					<div class="fill"></div>
				</div>
			</div>
			<div class="list flex flex-col">
				<div
					v-for="item of listValues"
					:key="JSON.stringify(item)"
					class="item group/item flex items-center gap-3"
					:class="[item.status]"
				>
					<div
						class="label flex items-center gap-2 truncate"
						:class="{ 'cursor-pointer': selectable }"
						@click="emit('select', item)"
					>
						<span class="badge"></span>
						<span
							class="truncate font-mono"
							:class="{ 'group-hover/item:text-primary transition-colors': selectable }"
						>
							{{ item.label }}
						</span>
						<Icon
							v-if="selectable"
							:name="icon || 'carbon:arrow-up-right'"
							class="group-hover/item:text-primary transition-colors"
						/>
					</div>
					<div class="divider grow"></div>
					<div class="value flex gap-3 font-mono whitespace-nowrap">
						<span v-if="!item.isTotal" class="opacity-50">{{ item.percentage }}%</span>
						<strong>{{ item.value }}</strong>
					</div>
				</div>
				<div v-if="!listValues.length" class="item group/item muted flex items-center gap-3">
					<div class="label flex items-center gap-2 truncate">
						<span class="badge"></span>
						<span class="truncate font-mono">No data</span>
					</div>
					<div class="divider grow"></div>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import _round from "lodash/round"
import { NCard } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

export interface ItemProps {
	value: number
	label: string
	isTotal?: boolean
	status?: "success" | "warning" | "error" | "muted" | "primary" | "default" | "info"
}

interface ItemPropsExt extends ItemProps {
	percentage: number
}

const {
	title,
	values,
	showTotal = true,
	showZeroItems,
	clickable,
	selectable,
	icon
} = defineProps<{
	title: string
	values: ItemProps[]
	icon?: string
	showTotal?: boolean
	showZeroItems?: boolean
	clickable?: boolean
	selectable?: boolean
}>()

const emit = defineEmits<{
	select: [item: ItemProps]
}>()

const totItem = computed(
	() =>
		values.find(item => item.isTotal) || {
			value: values.reduce((acc, cur) => {
				return acc + cur.value
			}, 0),
			isTotal: true,
			label: "Total"
		}
)

const sanitizedValues = computed<ItemPropsExt[]>(() => {
	const list: ItemPropsExt[] = values
		.filter(o => !o.isTotal)
		.map(o => ({ ...o, percentage: _round((o.value / totItem.value.value) * 100, 2) }))
		.filter(o => o.value || (!o.value && showZeroItems))

	return [{ ...totItem.value, percentage: 100 }, ...list]
})

const listValues = computed<ItemPropsExt[]>(() =>
	sanitizedValues.value.filter(o => !o.isTotal || (showTotal && o.isTotal))
)

const barValues = computed<ItemPropsExt[]>(() => sanitizedValues.value.filter(o => !o.isTotal && o.percentage))
</script>

<style scoped lang="scss">
@use "sass:list";

.n-card {
	overflow: hidden;

	.card-content {
		padding: 12px 16px;

		.bars {
			height: 10px;

			.bar {
				padding: 0 2px;

				&:first-child {
					padding-left: 0;
				}
				&:last-child {
					padding-right: 0;
				}

				.fill {
					border-radius: var(--border-radius-small);
					background-color: var(--fg-default-color);
					height: 100%;
					width: 100%;
				}

				@for $i from 2 through 10 {
					$opacities: (1, 0.8, 0.6, 0.4, 0.2);
					$idx: (($i - 1) % 5) + 1;
					&:nth-child(#{$i}) {
						.fill {
							opacity: list.nth($opacities, $idx);
						}
					}
				}

				&.success {
					.fill {
						background-color: var(--success-color);
						opacity: 1;
					}
				}
				&.warning {
					.fill {
						background-color: var(--warning-color);
						opacity: 1;
					}
				}
				&.error {
					.fill {
						background-color: var(--error-color);
						opacity: 1;
					}
				}
				&.muted {
					.fill {
						background-color: var(--fg-secondary-color);
						opacity: 1;
					}
				}
				&.info {
					.fill {
						background-color: var(--info-color);
						opacity: 1;
					}
				}
				&.primary {
					.fill {
						background-color: var(--primary-color);
						opacity: 1;
					}
				}
				&.default {
					.fill {
						background-color: var(--fg-default-color);
						opacity: 1;
					}
				}
			}
		}

		.list {
			font-size: 13px;
			gap: 4px;

			.item {
				line-height: 1;
				padding: 3px 4px;

				.badge {
					height: 10px;
					width: 10px;
					min-width: 10px;
					border-radius: var(--border-radius-small);
					background-color: var(--fg-default-color);
				}

				.divider {
					height: 1px;
					background-color: rgba(var(--border-color-rgb) / 0.7);
				}

				@for $i from 2 through 10 {
					$opacities: (1, 0.8, 0.6, 0.4, 0.2);
					$idx: (($i - 1) % 5) + 1;
					&:nth-child(#{$i}) {
						.badge {
							opacity: list.nth($opacities, $idx);
						}
					}
				}

				&.success {
					.badge {
						background-color: var(--success-color);
						opacity: 1;
					}
				}
				&.warning {
					.badge {
						background-color: var(--warning-color);
						opacity: 1;
					}
				}
				&.error {
					.badge {
						background-color: var(--error-color);
						opacity: 1;
					}
				}
				&.muted {
					.badge {
						background-color: var(--fg-secondary-color);
						opacity: 1;
					}
				}
				&.info {
					.badge {
						background-color: var(--info-color);
						opacity: 1;
					}
				}
				&.default {
					.badge {
						background-color: var(--fg-default-color);
						opacity: 1;
					}
				}
				&.primary {
					.badge {
						background-color: var(--primary-color);
						opacity: 1;
					}
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
