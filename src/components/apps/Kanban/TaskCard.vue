<template>
	<div class="task-card flex flex-col justify-between">
		<div class="task-header flex justify-between gap-3">
			<div class="task-title">{{ task.title }}</div>
			<Icon :size="20" class="pan-area" v-if="mobile" :name="PanIcon"></Icon>
		</div>
		<div class="task-footer flex justify-between items-end">
			<span class="task-date">{{ task.dateText }}</span>
			<span
				class="task-label custom-label"
				v-if="task.label"
				:style="`--label-color:${labelsColors[task.label.id]}`"
			>
				{{ task.label.title }}
			</span>
		</div>
	</div>
</template>
<script lang="ts" setup>
import Icon from "@/components/common/Icon.vue"
const PanIcon = "carbon:move"
import { type Task } from "@/mock/kanban"
import { toRefs, computed } from "vue"
import { useThemeStore } from "@/stores/theme"

const props = defineProps<{
	task: Task
	mobile: boolean
}>()
const { task, mobile } = toRefs(props)

const secondaryColors = computed(() => useThemeStore().secondaryColors)

const labelsColors = {
	design: secondaryColors.value["secondary1"],
	"feature-request": secondaryColors.value["secondary2"],
	backend: secondaryColors.value["secondary3"],
	qa: secondaryColors.value["secondary4"]
} as unknown as { [key: string]: string }
</script>

<style lang="scss" scoped>
.task-card {
	cursor: move;
	border-radius: var(--border-radius-small);
	padding: 8px 10px;
	margin-bottom: 10px;
	margin-top: 3px;
	background-color: var(--bg-color);
	transition: all 0.2s;
	opacity: 0;
	animation: task-fade 0.3s forwards;
	border: 1px solid var(--border-color);

	@for $i from 0 through 15 {
		&:nth-child(#{$i}) {
			animation-delay: $i * 0.1s;
		}
	}

	@keyframes task-fade {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
		}
	}

	.pan-area {
		margin-top: 2px;
	}

	.task-title {
		font-weight: bold;
		font-size: 15px;
		line-height: 1.3;
	}

	.task-footer {
		margin-top: 14px;
		.task-date {
			font-size: 14px;
			opacity: 0.8;
		}
	}

	&:hover {
		border-color: var(--primary-color);
	}
}
</style>
