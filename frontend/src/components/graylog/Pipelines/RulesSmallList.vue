<template>
	<div class="flex flex-col">
		<n-button
			v-for="rule of rules"
			:key="rule.id"
			quaternary
			size="tiny"
			class="group min-w-full [&_.n-button__content]:min-w-full"
			@click="emit('click', rule.id)"
		>
			<div class="flex max-w-67.5 items-center overflow-hidden">
				<span class="min-w-6">
					<Icon
						:name="ViewIcon"
						:size="16"
						class="opacity-0 transition-opacity duration-200 group-hover:opacity-100"
					/>
				</span>
				<span class="grow truncate">
					{{ rule.title }}
				</span>
				<span class="min-w-5"></span>
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
