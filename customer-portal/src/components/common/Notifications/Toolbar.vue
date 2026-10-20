<template>
	<div class="flex w-full" :class="{ 'justify-between': showClear, 'justify-end': !showClear }">
		<n-button v-if="showClear" quaternary @click="bell.deleteAll()">Clear</n-button>
		<n-button
			strong
			secondary
			type="primary"
			:disabled="!hasUnread"
			data-testid="notifications-mark-all-read"
			@click="bell.setAllRead()"
		>
			Mark all as read
		</n-button>
	</div>
</template>

<script lang="ts" setup>
import { NButton } from "naive-ui"
import { computed } from "vue"
import { useBell } from "@/composables/common/useBell"

const bell = useBell()
const hasUnread = bell.hasUnread
// Server notifications are only marked read, never cleared (#1282).
const showClear = computed(() => bell.hasNotifications.value && bell.canDelete.value)
</script>
