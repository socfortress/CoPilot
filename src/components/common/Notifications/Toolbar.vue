<template>
	<div
		class="notifications-toolbar flex"
		:class="{ 'justify-between': hasNotifications, 'justify-end': !hasNotifications }"
	>
		<n-button quaternary @click="deleteAll()" v-if="hasNotifications">Clear</n-button>
		<n-button strong secondary type="primary" :disabled="!hasUnread" @click="setAllRead()">
			Mark all as read
		</n-button>
	</div>
</template>

<script lang="ts" setup>
import { NButton } from "naive-ui"
import { useNotifications } from "@/composables/useNotifications"

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
