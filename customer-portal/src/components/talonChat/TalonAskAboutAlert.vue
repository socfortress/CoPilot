<template>
	<div v-if="enabled" class="flex justify-end" data-testid="talon-ask-about-alert">
		<n-button size="small" secondary :loading="opening" :disabled="opening" data-testid="talon-ask-about-alert-button" @click="ask()">
			<template #icon><Icon name="carbon:chat-bot" /></template>
			{{ $t("talonChat.askAboutAlert.button") }}
		</n-button>
	</div>
</template>

<script setup lang="ts">
import type { TalonChatThread } from "@/types/talonChat"
import { NButton, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import { useLocalesStore } from "@/stores/i18n"
import { errorCodeOf, errorText } from "./talonChat"

/**
 * "Ask Talon about this alert" (talon-analyst D97): goes to the user's open conversation about
 * this alert, or opens one with the alert as its context, for the alert's own customer. Shown only
 * when Ask Talon is on for that customer; read-only users too, since chatting is reading. A thread
 * is made only on the click, never by opening a link, so a reload or a shared address makes no
 * second one; and a second click finds the first instead of using up the thread limits.
 */
const { alertId, customerCode } = defineProps<{
	alertId: number
	customerCode: string
}>()

/** The most active portal threads a user may have is 10 (talon-analyst): one page holds them all. */
const SEARCH_LIMIT = 50

const router = useRouter()
const toast = useMessage()
const localesStore = useLocalesStore()
const { isEnabledFor, invalidate } = useTalonChatAvailability()

const enabled = ref(false)
const opening = ref(false)

function isThisAlerts(thread: TalonChatThread) {
	return (
		thread.context_alert_id === alertId &&
		thread.customer_code === customerCode &&
		thread.status === "active" &&
		thread.accessible
	)
}

/** The user's open, usable conversation about this alert, if any. A failed search finds none. */
async function existing(): Promise<TalonChatThread | null> {
	try {
		const res = await Api.talonChat.listThreads({ status: "active", limit: SEARCH_LIMIT })
		return (res.data.threads ?? []).find(isThisAlerts) ?? null
	} catch {
		return null
	}
}

async function ask() {
	if (opening.value) return
	opening.value = true
	try {
		const found = await existing()
		const thread =
			found ??
			(
				await Api.talonChat.createThread({
					customer_code: customerCode,
					alert_id: alertId,
					language: localesStore.locale
				})
			).data
		await router.push({ name: "TalonChat", query: { thread: thread.id } })
	} catch (err) {
		const code = errorCodeOf(err)
		if (code === "portal_off") {
			invalidate(customerCode)
			enabled.value = false
		}
		toast.error(errorText(code))
	} finally {
		opening.value = false
	}
}

watch(
	() => customerCode,
	async code => {
		enabled.value = false
		enabled.value = code ? await isEnabledFor(code) : false
	},
	{ immediate: true }
)
</script>
