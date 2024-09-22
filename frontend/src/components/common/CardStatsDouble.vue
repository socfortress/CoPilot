<template>
	<n-card content-style="padding:0" :class="{ hovered }">
		<div class="flex flex-col overflow-hidden">
			<div class="card-header flex gap-4 items-center justify-between">
				<div class="title flex items-center gap-2">
					{{ title }}
					<Icon v-if="hovered" :name="ArrowRightIcon" :size="12"></Icon>
				</div>
				<div class="icon">
					<slot name="icon"></slot>
				</div>
			</div>
			<div class="flex card-content">
				<div class="flex flex-col basis-1/2 value-box" :class="firstStatus">
					<div class="value">
						{{ value }}
					</div>
					<div v-if="firstLabel" class="label">
						{{ firstLabel }}
					</div>
				</div>
				<div class="flex flex-col basis-1/2 value-box" :class="secondStatus">
					<div class="value">
						{{ subValue }}
					</div>
					<div v-if="secondLabel" class="label">
						{{ secondLabel }}
					</div>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { NCard } from "naive-ui"
import { toRefs } from "vue"

const props = defineProps<{
	title: string
	value?: number | string
	subValue?: number | string
	firstLabel?: string
	secondLabel?: string
	firstStatus?: "success" | "warning" | "error"
	secondStatus?: "success" | "warning" | "error"
	hovered?: boolean
}>()
const { title, value, subValue, firstLabel, secondLabel, firstStatus, secondStatus, hovered } = toRefs(props)

const ArrowRightIcon = "carbon:arrow-right"
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
		.value-box {
			text-align: center;
			overflow: hidden;

			&:first-child {
				border-right: var(--border-small-050);
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
				border-top: var(--border-small-050);
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
