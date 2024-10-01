<template>
	<n-card content-style="padding:0" :class="{ hovered }">
		<div class="flex flex-col overflow-hidden">
			<div class="card-header flex gap-4 items-center justify-between">
				<div class="title flex items-center gap-2 grow">
					<span class="truncate">{{ title }}</span>
					<Icon v-if="hovered" :name="ArrowRightIcon" :size="12"></Icon>
				</div>
				<div class="icon">
					<slot name="icon"></slot>
				</div>
			</div>
			<div class="flex flex-col gap-3 card-content">
				<div class="bars flex">
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
						v-for="item of sanitizedValues"
						:key="JSON.stringify(item)"
						class="flex items-center item gap-3"
						:class="item.status"
					>
						<div class="label flex gap-2 items-center truncate">
							<span class="badge"></span>
							<span class="font-mono truncate">{{ item.label }}</span>
						</div>
						<div class="divider grow"></div>
						<div class="value flex gap-3 font-mono whitespace-nowrap">
							<span v-if="!item.isTotal" class="opacity-50">{{ item.percentage }}%</span>
							<strong>{{ item.value }}</strong>
						</div>
					</div>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import _round from "lodash/round"
import { NCard } from "naive-ui"
import { computed, toRefs } from "vue"

export interface ItemProps {
	value: number
	label: string
	isTotal?: boolean
	status?: "success" | "warning" | "error" | "muted" | "primary"
}

interface ItemPropsExt extends ItemProps {
	percentage: number
}

const props = defineProps<{
	title: string
	values: ItemProps[]
	showZeroItems?: boolean
	hovered?: boolean
}>()
const { title, values, showZeroItems, hovered } = toRefs(props)

const ArrowRightIcon = "carbon:arrow-right"
const totItem = computed(
	() =>
		values.value.find(item => item.isTotal) || {
			value: values.value.reduce((acc, cur) => {
				return acc + cur.value
			}, 0),
			isTotal: true,
			label: "Total"
		}
)

const sanitizedValues = computed<ItemPropsExt[]>(() => {
	const list: ItemPropsExt[] = values.value
		.filter(o => !o.isTotal)
		.map(o => ({ ...o, percentage: _round((o.value / totItem.value.value) * 100, 2) }))
		.filter(o => o.value || (!o.value && showZeroItems.value))

	return [{ ...totItem.value, percentage: 100 }, ...list]
})

const barValues = computed<ItemPropsExt[]>(() => sanitizedValues.value.filter(o => !o.isTotal && o.percentage))
</script>

<style scoped lang="scss">
.n-card {
	overflow: hidden;

	.card-header {
		border-bottom: var(--border-small-050);
		overflow: hidden;
		padding: 10px 16px;

		.title {
			font-size: 16px;
			text-overflow: ellipsis;
			white-space: nowrap;
			overflow: hidden;
		}
	}

	.card-content {
		padding: 10px 16px;

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
					background-color: var(--fg-color);
					height: 100%;
					width: 100%;
				}

				&.success {
					.fill {
						background-color: var(--success-color);
					}
				}
				&.warning {
					.fill {
						background-color: var(--warning-color);
					}
				}
				&.error {
					.fill {
						background-color: var(--error-color);
					}
				}
				&.muted {
					.fill {
						background-color: var(--fg-secondary-color);
					}
				}
				&.primary {
					.fill {
						background-color: var(--primary-color);
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
					background-color: var(--fg-color);
				}

				.divider {
					height: 1px;
					background-color: var(--hover-010-color);
				}

				&.success {
					.badge {
						background-color: var(--success-color);
					}
				}
				&.warning {
					.badge {
						background-color: var(--warning-color);
					}
				}
				&.error {
					.badge {
						background-color: var(--error-color);
					}
				}
				&.muted {
					.badge {
						background-color: var(--fg-secondary-color);
					}
				}
				&.primary {
					.badge {
						background-color: var(--primary-color);
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
