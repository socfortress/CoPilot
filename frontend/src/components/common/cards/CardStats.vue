<template>
	<n-card :class="{ hovered }">
		<div class="flex h-full items-center overflow-hidden">
			<div class="card-wrap flex gap-4" :class="{ 'flex-col items-center text-center': vertical }">
				<div class="icon flex flex-col justify-center">
					<slot name="icon"></slot>
				</div>
				<div class="info flex grow flex-col overflow-hidden">
					<div class="title flex items-center gap-2">
						{{ title }}
						<Icon v-if="hovered" :name="ArrowRightIcon" :size="12"></Icon>
					</div>
					<div v-if="value" class="value mt-1">
						{{ value }}
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

const props = defineProps<{
	title: string
	value?: number | string
	vertical?: boolean
	hovered?: boolean
}>()
const { title, value, vertical, hovered } = toRefs(props)

const ArrowRightIcon = "carbon:arrow-right"
</script>

<style scoped lang="scss">
.n-card {
	overflow: hidden;

	.card-wrap {
		width: 100%;
		overflow: hidden;

		.title {
			font-size: 16px;
			text-overflow: ellipsis;
			white-space: nowrap;
			overflow: hidden;
		}

		.value {
			font-family: var(--font-family-display);
			font-size: 22px;
			font-weight: bold;
			text-overflow: ellipsis;
			white-space: nowrap;
			overflow: hidden;
		}
	}

	&.hovered {
		&:hover {
			border-color: var(--primary-color);
		}
	}
}
</style>
