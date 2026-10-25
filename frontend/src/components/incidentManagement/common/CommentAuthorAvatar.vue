<template>
	<div class="relative shrink-0" :title="role ? `${userName} · ${roleLabel(role)}` : userName" data-testid="comment-author-avatar">
		<n-avatar
			round
			:size
			:src="userPic"
			:img-props="{ alt: '' }"
			:style="role ? { boxShadow: `0 0 0 2px ${roleColor(role)}` } : undefined"
		/>
		<span
			v-if="role"
			class="border-default absolute -right-1 -bottom-1 flex size-4 items-center justify-center rounded-full border"
			:style="{ background: roleColor(role) }"
			:data-role="role"
			data-testid="comment-author-role-badge"
		>
			<Icon :name="roleIcon(role)" :size="10" class="text-white" />
		</span>
	</div>
</template>

<script setup lang="ts">
import { NAvatar } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { roleColor, roleIcon, roleLabel } from "@/components/users/roles"
import { getAvatar, getNameInitials } from "@/utils"

/**
 * A comment author's avatar with their role on it: ringed in the role's colour, its icon in a
 * badge at the corner, like the toolbar's and the Profile's (#1296). No role (a pipeline's
 * signature, a deleted user, not read yet): the plain avatar.
 */
const { userName, role = null, size = 32 } = defineProps<{
	userName: string
	role?: string | null
	size?: number
}>()

const userPic = computed(() => {
	const initials = getNameInitials(userName)
	return getAvatar({ seed: initials, text: initials, size: 64 })
})
</script>
