<template>
	<div class="alert-comment-item flex gap-3" :class="{ embedded }">
		<div v-if="userPic" class="user-pic">
			<n-avatar round :size="32" :src="userPic" />
		</div>
		<div class="comment flex grow flex-col gap-1">
			<div class="user flex items-center gap-3">
				<div class="user-name">
					{{ comment.user_name }}
				</div>
				<div class="comment-time">
					{{ formatDate(comment.created_at, dFormats.datetime) }}
				</div>
			</div>
			<div class="comment-message" v-html="message"></div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { AlertComment } from "@/types/incidentManagement/alerts.d"
import { useSettingsStore } from "@/stores/settings"
import { formatDate, getAvatar, getNameInitials } from "@/utils"
import { NAvatar } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"

const props = defineProps<{ comment: AlertComment; embedded?: boolean }>()
const { comment, embedded } = toRefs(props)

const dFormats = useSettingsStore().dateFormat
const userPic = ref("")
const message = ref(comment.value.comment.replace(/\n/g, "<br/>"))

onBeforeMount(() => {
	const initials = getNameInitials(comment.value.user_name)
	userPic.value = getAvatar({ seed: initials, text: initials, size: 64 })
})
</script>

<style lang="scss" scoped>
.alert-comment-item {
	width: 100%;

	.user-pic {
		padding-top: 4px;
	}

	.comment {
		.user {
			margin-left: 2px;

			.user-name {
				font-weight: 600;
			}

			.comment-time {
				font-size: 11px;
				color: var(--fg-secondary-color);
				font-family: var(--font-family-mono);
			}
		}

		.comment-message {
			border-radius: var(--border-radius);
			background-color: var(--bg-color);
			border: var(--border-small-050);
			padding: 6px 10px;
		}
	}

	&.embedded {
		.comment {
			.comment-message {
				background-color: var(--bg-secondary-color);
			}
		}
	}
}
</style>
