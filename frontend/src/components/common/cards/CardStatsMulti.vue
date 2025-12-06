<template>
	<n-card content-class="p-0!" :class="{ hovered }">
		<div class="flex h-full flex-col overflow-hidden">
			<div class="card-header flex items-center justify-between gap-4">
				<div class="title flex grow items-center gap-2">
					<span class="truncate">{{ title }}</span>
					<Icon v-if="hovered" :name="ArrowRightIcon" :size="12" />
				</div>
				<div class="icon">
					<slot name="icon"></slot>
				</div>
			</div>
			<div class="card-content flex grow">
				<div
					v-for="item of values"
					:key="JSON.stringify(item)"
					class="value-box flex flex-col"
					:class="[item.status, values.length !== 1 ? `basis-1/${values.length}` : 'grow']"
				>
					<div class="value flex grow items-center justify-center">
						{{ item.value }}
					</div>
					<div v-if="item.label" class="label">
						{{ item.label }}
					</div>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import { toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"

export interface ItemProps {
	value: number | string
	label?: string
	status?: "success" | "warning" | "error"
}

const props = defineProps<{
	title: string
	values: ItemProps[]
	hovered?: boolean
}>()
const { title, values, hovered } = toRefs(props)

const ArrowRightIcon = "carbon:arrow-right"
</script>

<style scoped lang="scss">
.n-card {
	overflow: hidden;

	.card-header {
		border-bottom: 1px solid var(--border-color);
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
		.value-box {
			text-align: center;
			overflow: hidden;

			&:not(:last-child) {
				border-right: 1px solid var(--border-color);
			}

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
