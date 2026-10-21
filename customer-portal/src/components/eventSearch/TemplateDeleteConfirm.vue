<template>
	<div
		class="bg-error/5 flex min-w-0 grow flex-wrap items-center gap-x-2 gap-y-1.5 px-3 py-2"
		role="alertdialog"
		:aria-label="`Delete the template “${name}”?`"
		data-testid="template-delete-confirm"
		@keydown.esc.stop="emit('cancel')"
	>
		<!-- The name in full, wrapping when the row is narrow: it is what is being confirmed. -->
		<span class="flex min-w-36 grow basis-0 items-start gap-2">
			<Icon name="carbon:warning-alt" :size="14" class="text-error mt-px shrink-0" />
			<span class="text-default min-w-0 text-xs break-words">
				Delete
				<span class="font-medium">“{{ name }}”</span>
				<!-- Its own element: a line break between two elements renders as nothing, so "?" stays
				     beside the name however the formatter wraps this. -->
				<span>?</span>
			</span>
		</span>
		<span class="ml-auto flex shrink-0 gap-2">
			<n-button
				ref="cancelButton"
				size="tiny"
				quaternary
				data-testid="template-delete-cancel"
				@click="emit('cancel')"
			>
				Cancel
			</n-button>
			<n-button
				size="tiny"
				type="error"
				secondary
				:loading
				data-testid="template-delete-confirm-button"
				@click="emit('confirm')"
			>
				Delete
			</n-button>
		</span>
	</div>
</template>

<script setup lang="ts">
import { NButton } from "naive-ui"
import { onMounted, useTemplateRef } from "vue"
import Icon from "@/components/common/Icon.vue"

/**
 * The confirmation a template's deletion asks for (#1258), in place of the row it deletes:
 * nothing is deleted until Delete is pressed. Focus lands on Cancel, so Enter cannot delete
 * by accident; Escape cancels.
 */

const { name, loading = false } = defineProps<{
	name: string
	loading?: boolean
}>()

const emit = defineEmits<{
	(e: "confirm"): void
	(e: "cancel"): void
}>()

const cancelButton = useTemplateRef<InstanceType<typeof NButton>>("cancelButton")
onMounted(() => cancelButton.value?.$el?.focus?.())
</script>
