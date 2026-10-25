import type { MaybeRefOrGetter } from "vue"
import { ref, toValue, watch } from "vue"
import Api from "@/api"
import { roleNameOf } from "@/components/users/roles"
import { useAuthStore } from "@/stores/auth"

/**
 * The role of each author of an alert's or a case's comments (#1305), for the role badges on
 * their avatars. Read once per alert or case; a comment the signed-in user writes takes their
 * own role straight away. A failed read only leaves the badges out.
 */
export function useCommentAuthors(entity: "alert" | "case", entityId: MaybeRefOrGetter<number>) {
	const authStore = useAuthStore()
	const authors = ref<Record<string, string>>({})

	async function load() {
		const id = toValue(entityId)
		try {
			const res =
				entity === "alert"
					? await Api.incidentManagement.alerts.getAlertCommentAuthors(id)
					: await Api.incidentManagement.cases.getCaseCommentAuthors(id)
			if (id === toValue(entityId)) authors.value = res.data.authors ?? {}
		} catch {
			// No role badges: the comments still show.
		}
	}

	function roleOf(userName: string | null | undefined): string | null {
		if (!userName) return null
		if (authors.value[userName]) return authors.value[userName]
		return userName === authStore.userName ? roleNameOf(authStore.userRole) || null : null
	}

	watch(
		() => toValue(entityId),
		() => {
			authors.value = {}
			load()
		},
		{ immediate: true }
	)

	return { authors, load, roleOf }
}
