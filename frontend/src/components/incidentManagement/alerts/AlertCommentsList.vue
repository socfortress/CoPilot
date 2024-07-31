<template>
	<div class="flex flex-col gap-2">
		<template v-if="comments.length">
			<AlertCommentItem :comment embedded v-for="comment of comments" :key="comment.id" />
		</template>
		<template v-else>
			<n-empty description="No items found" class="justify-center h-48" />
		</template>
	</div>
</template>

<script setup lang="ts">
import { toRefs } from "vue"
import { NEmpty } from "naive-ui"
import AlertCommentItem from "./AlertComment.vue"
import type { AlertComment } from "@/types/incidentManagement/alerts.d"

const props = defineProps<{ comments: AlertComment[] }>()
const { comments } = toRefs(props)
</script>
