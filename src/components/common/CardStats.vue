<template>
	<n-card>
		<div class="flex items-center h-full overflow-hidden">
			<div class="card-wrap flex gap-4" :class="{ 'flex-col items-center text-center': vertical }">
				<div class="icon flex flex-col justify-center">
					<slot name="icon"></slot>
				</div>
				<div class="info flex flex-col grow overflow-hidden">
					<div class="title">{{ title }}</div>
					<div class="value mt-1" v-if="value">{{ value }}</div>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import { toRefs } from "vue"

const props = defineProps<{
	title: string
	value?: number | string
	vertical?: boolean
}>()
const { title, value, vertical } = toRefs(props)
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
}
</style>
