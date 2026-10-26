<template>
	<div
		class="bg-error/5 flex min-w-0 grow flex-wrap items-center gap-x-2 gap-y-1.5 px-3 py-2"
		role="alertdialog"
		:aria-label="$t('eventSearch.deleteConfirm.label', { name })"
		data-testid="template-delete-confirm"
		@keydown.esc.stop="emit('cancel')"
	>
		<!-- The name in full, wrapping when the row is narrow: it is what is being confirmed. -->
		<span class="flex min-w-36 grow basis-0 items-start gap-2">
			<Icon name="carbon:warning-alt" :size="14" class="text-error mt-px shrink-0" />
			<i18n-t keypath="eventSearch.deleteConfirm.question" tag="span" class="text-default min-w-0 text-xs break-words">
				<template #name>
					<span class="font-medium">“{{ name }}”</span>
				</template>
			</i18n-t>
		</span>
		<span class="ml-auto flex shrink-0 gap-2">
			<n-button
				ref="cancelButton"
				size="tiny"
				quaternary
				data-testid="template-delete-cancel"
				@click="emit('cancel')"
			>
				{{ $t("common.actions.cancel") }}
			</n-button>
			<n-button
				size="tiny"
				type="error"
				secondary
				:loading
				data-testid="template-delete-confirm-button"
				@click="emit('confirm')"
			>
				{{ $t("common.actions.delete") }}
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
