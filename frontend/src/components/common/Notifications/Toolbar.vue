<template>
	<div
		class="notifications-toolbar flex"
		:class="{ 'justify-between': hasNotifications, 'justify-end': !hasNotifications }"
	>
		<n-button v-if="hasNotifications" quaternary @click="deleteAll()">Clear</n-button>
		<n-button strong secondary type="primary" :disabled="!hasUnread" @click="setAllRead()">
			Mark all as read
		</n-button>
	</div>
</template>

<script lang="ts" setup>
import { useNotifications } from "@/composables/useNotifications"
import { NButton } from "naive-ui"

const hasUnread = useNotifications().hasUnread
const hasNotifications = useNotifications().hasNotifications

function setAllRead() {
	useNotifications().setAllRead()
}

function deleteAll() {
	useNotifications().deleteAll()
}
</script>

<style>
.notifications-toolbar {
	width: 100%;
}
</style>
