<template>
	<div
		class="segmented-toggle border-default bg-secondary inline-flex h-5.5 items-stretch rounded-md border p-px"
		role="radiogroup"
		:aria-label="label"
		:data-testid="testId"
		@keydown="onKeydown"
	>
		<button
			v-for="(option, index) of options"
			:key="String(option.value)"
			ref="buttons"
			type="button"
			role="radio"
			:aria-checked="option.value === model"
			:tabindex="option.value === model ? 0 : -1"
			class="segment text-3xs flex cursor-pointer items-center rounded-[5px] px-2 font-mono leading-none tracking-wider uppercase transition-colors"
			:class="{ 'is-active': option.value === model }"
			:data-testid="testId ? `${testId}-${option.value}` : undefined"
			@click="select(index)"
		>
			{{ option.label }}
		</button>
	</div>
</template>

<script setup lang="ts" generic="T extends string | number">
// A compact segmented switch — a few mutually exclusive choices in one small control,
// for places a Naive radio group (28px) is too tall: a panel or card header, a toolbar.
// 22px, like a tiny button, so it never makes a header taller than its label strip. One
// radio group to assistive tech; arrow keys move the choice, and only the chosen segment
// is in the tab order. Values are strings or numbers (the component is generic over them).
import { shallowRef } from "vue"

const { options, label, testId } = defineProps<{
	options: { value: T; label: string }[]
	/** Accessible name of the group, e.g. "Show". */
	label: string
	testId?: string
}>()

const model = defineModel<T>({ required: true })

const buttons = shallowRef<HTMLButtonElement[]>([])

function select(index: number) {
	model.value = options[index].value
}

function onKeydown(event: KeyboardEvent) {
	const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key]
	if (!step) return
	event.preventDefault()
	const current = options.findIndex(option => option.value === model.value)
	const next = (current + step + options.length) % options.length
	select(next)
	buttons.value[next]?.focus()
}
</script>

<style scoped>
.segment {
	color: var(--fg-secondary-color);
}

.segment:hover {
	color: var(--fg-default-color);
}

.segment:focus-visible {
	outline: 1px solid var(--primary-color);
	outline-offset: 1px;
}

.segment.is-active {
	color: var(--primary-color);
	background-color: var(--bg-default-color);
	box-shadow: 0 0 0 1px rgb(var(--primary-color-rgb) / 0.35);
}
</style>
