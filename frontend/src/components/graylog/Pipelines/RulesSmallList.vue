<template>
	<div class="rules-list flex flex-col">
		<n-button v-for="rule of rules" :key="rule.id" quaternary size="tiny" @click="emit('click', rule.id)">
			<div class="btn-wrap flex items-center">
				<span class="spacer">
					<Icon :name="ViewIcon" :size="16"></Icon>
				</span>
				<span class="title grow">
					{{ rule.title }}
				</span>
				<span class="spacer small"></span>
			</div>
		</n-button>
	</div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import { toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"

export interface RuleExtended {
	title: string
	id: string
}

const props = defineProps<{ rules: RuleExtended[] }>()

const emit = defineEmits<{
	(e: "click", value: string): void
}>()

const { rules } = toRefs(props)

const ViewIcon = "iconoir:eye-solid"
</script>

<style lang="scss" scoped>
.rules-list {
	.n-button {
		min-width: 100%;

		:deep(.n-button__content) {
			min-width: 100%;
		}

		.btn-wrap {
			max-width: 270px;
			overflow: hidden;

			.title {
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
			}

			.spacer {
				min-width: 24px;

				&.small {
					min-width: 20px;
				}
			}
		}

		i {
			opacity: 0;
			transition: opacity 0.2s;
		}

		&:hover {
			i {
				opacity: 1;
			}
		}
	}
}
</style>
