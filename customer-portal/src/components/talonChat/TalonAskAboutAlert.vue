<template>
	<div v-if="enabled" class="flex justify-end" data-testid="talon-ask-about-alert">
		<n-button size="small" secondary :loading="creating" :disabled="creating" data-testid="talon-ask-about-alert-button" @click="ask()">
			<template #icon><Icon name="carbon:chat-bot" /></template>
			{{ $t("talonChat.askAboutAlert.button") }}
		</n-button>
	</div>
</template>

<script setup lang="ts">
import { NButton, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import { errorCodeOf, errorText } from "./talonChat"

/**
 * "Ask Talon about this alert" (talon-analyst D97): opens a conversation with the alert as its
 * context, for the alert's own customer, and goes to it. Shown only when Ask Talon is on for that
 * customer; read-only users too, since chatting is reading. The thread is made on the click, never
 * by opening a link, so a reload or a shared address makes no second one.
 */
const { alertId, customerCode } = defineProps<{
	alertId: number
	customerCode: string
}>()

const router = useRouter()
const toast = useMessage()
const { isEnabledFor } = useTalonChatAvailability()

const enabled = ref(false)
const creating = ref(false)

async function ask() {
	if (creating.value) return
	creating.value = true
	try {
		const res = await Api.talonChat.createThread({ customer_code: customerCode, alert_id: alertId })
		await router.push({ name: "TalonChat", query: { thread: res.data.id } })
	} catch (err) {
		toast.error(errorText(errorCodeOf(err)))
	} finally {
		creating.value = false
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
