<template>
	<n-spin :show="loading" class="min-h-40">
		<UserDetails v-if="user" :user @deleted="emit('deleted')" />
		<n-empty v-else-if="!loading" :description="emptyText" class="py-10" data-testid="user-details-missing" />
	</n-spin>
</template>

<script setup lang="ts">
// UserDetails for callers that only know a username — an assignee, an actor in a log.
// The user list is searched by that name and only an exact match is shown: the search
// is a substring match, so "ana" must not open "anastasia".
import type { User } from "@/types/user"
import { NEmpty, NSpin } from "naive-ui"
import { computed, shallowRef, watch } from "vue"
import Api from "@/api"
import UserDetails from "./UserDetails.vue"

const { username } = defineProps<{ username: string }>()
const emit = defineEmits<{ (e: "loaded", value: User): void; (e: "deleted"): void }>()

const user = shallowRef<User | null>(null)
const loading = shallowRef(false)
const failed = shallowRef(false)

const emptyText = computed(() =>
	failed.value ? "Could not load this user." : `No CoPilot user is called "${username}" any more.`
)

watch(
	() => username,
	async (name, _old, onCleanup) => {
		const controller = new AbortController()
		onCleanup(() => controller.abort())
		loading.value = true
		failed.value = false
		user.value = null
		try {
			const response = await Api.users.getUsers({ search: name, limit: 50 }, controller.signal)
			user.value = (response.data.users ?? []).find(candidate => candidate.username === name) ?? null
			if (user.value) emit("loaded", user.value)
		} catch {
			if (controller.signal.aborted) return
			failed.value = true
		} finally {
			if (!controller.signal.aborted) loading.value = false
		}
	},
	{ immediate: true }
)
</script>
