<template>
	<div class="flex shrink-0 items-center justify-end" :class="compact ? 'gap-1' : 'gap-2'">
		<n-button
			size="tiny"
			quaternary
			:aria-label="compact ? 'Edit fact' : undefined"
			:title="compact ? 'Edit' : undefined"
			data-testid="knowledge-fact-edit"
			@click="emit('edit')"
		>
			<template #icon>
				<Icon :name="EditIcon" :size="14" />
			</template>
			<template v-if="!compact">Edit</template>
		</n-button>

		<n-popconfirm to="body" @positive-click="emit('delete')">
			<template #trigger>
				<n-button
					size="tiny"
					quaternary
					:loading="deleting"
					:aria-label="compact ? 'Delete fact' : undefined"
					:title="compact ? 'Delete' : undefined"
					data-testid="knowledge-fact-delete"
				>
					<template #icon>
						<Icon :name="DeleteIcon" :size="14" />
					</template>
					<template v-if="!compact">Delete</template>
				</n-button>
			</template>
			Delete this fact? talon-analyst stops reading it. The audit log keeps what it held.
		</n-popconfirm>
	</div>
</template>

<script setup lang="ts">
import { NButton, NPopconfirm } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

/** A fact's Edit and Delete: worded in a card, icons alone (named for screen readers) in a row. */
const { compact = false, deleting = false } = defineProps<{
	compact?: boolean
	deleting?: boolean
}>()

const emit = defineEmits<{
	(e: "edit"): void
	/** Confirmed: the fact should go. */
	(e: "delete"): void
}>()

const EditIcon = "carbon:edit"
const DeleteIcon = "carbon:trash-can"
</script>
