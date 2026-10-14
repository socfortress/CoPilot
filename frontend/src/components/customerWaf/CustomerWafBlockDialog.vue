<template>
	<n-modal
		v-model:show="show"
		preset="card"
		title="Block at WAF"
		:style="{ maxWidth: 'min(560px, 92vw)' }"
		segmented
		:mask-closable="!submitting"
	>
		<div class="flex flex-col gap-4">
			<n-alert v-if="!blockable.length" type="warning" :bordered="false">
				This customer has no enabled WAF whose token can block. Blocking needs a token whose WAF user has the
				<b>admin</b>
				or
				<b>operator</b>
				role. Run a connection test on the WAF after changing its token.
			</n-alert>

			<n-form label-placement="top" :show-feedback="false" class="flex flex-col gap-4">
				<n-form-item v-if="blockable.length > 1" label="WAF">
					<n-select v-model:value="wafId" :options="wafOptions" />
				</n-form-item>
				<div v-else-if="blockable.length === 1" class="text-secondary text-sm">
					WAF:
					<b>{{ blockable[0]?.name }}</b>
					<span class="font-mono text-xs">({{ blockable[0]?.api_url }})</span>
				</div>

				<n-form-item label="IP address or range">
					<n-input v-model:value="target" placeholder="203.0.113.7 or 203.0.113.0/24" class="font-mono" />
				</n-form-item>

				<n-form-item label="Reason">
					<n-input
						v-model:value="reason"
						type="textarea"
						:autosize="{ minRows: 2, maxRows: 5 }"
						:maxlength="500"
						show-count
						placeholder="Why — saved on the WAF rule's description, with your username"
					/>
				</n-form-item>
			</n-form>

			<p class="text-secondary text-xs">
				The WAF blocks the address traffic arrives from. If the WAF sits behind a load balancer, proxy or VPN,
				that is the shared exit — blocking it blocks everyone behind it.
			</p>

			<n-alert v-if="result" :type="result.type" :bordered="false">
				<div class="flex flex-col gap-1 text-sm">
					<span>{{ result.message }}</span>
					<span v-for="w of result.warnings" :key="w" class="text-xs">{{ w }}</span>
				</div>
			</n-alert>
		</div>

		<template #footer>
			<div class="flex justify-end gap-3">
				<n-button :disabled="submitting" @click="show = false">{{ result ? "Close" : "Cancel" }}</n-button>
				<n-button type="error" :loading="submitting" :disabled="!canSubmit" @click="submit()">
					<template #icon>
						<Icon :name="BlockIcon" />
					</template>
					Block
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerWafBlockAction, CustomerWafInstance } from "@/types/customer-waf"
import { NAlert, NButton, NForm, NFormItem, NInput, NModal, NSelect, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import { capabilitiesFromRoles, reasonHint } from "./utils"

const props = defineProps<{
	customerCode: string
	instances: CustomerWafInstance[]
	/** Pre-filled target, e.g. the IoC or offender IP. */
	initialTarget?: string
	/** The alert this block responds to — gets a reverse-link comment. */
	alertId?: number | null
}>()

const emit = defineEmits<{
	(e: "blocked", value: { wafId: number; action: CustomerWafBlockAction; target: string }): void
}>()

const show = defineModel<boolean>("show", { default: false })

const BlockIcon = "carbon:locked"
const message = useMessage()

const blockable = computed(() =>
	props.instances.filter(i => i.enabled && capabilitiesFromRoles(i.last_verified_role).can_block)
)
const wafOptions = computed(() => blockable.value.map(i => ({ label: `${i.name} — ${i.api_url}`, value: i.id })))

const wafId = ref<number | null>(null)
const target = ref("")
const reason = ref("")
const submitting = ref(false)
// Only a failure is shown in the dialog; success closes it.
const result = ref<{ type: "error"; message: string; warnings: string[] } | null>(null)

const canSubmit = computed(() => !!wafId.value && !!target.value.trim() && !!reason.value.trim() && !result.value)

watch(show, open => {
	if (!open) return
	wafId.value = blockable.value[0]?.id ?? null
	target.value = props.initialTarget ?? ""
	reason.value = props.alertId ? `Responding to alert #${props.alertId}` : ""
	result.value = null
})

/**
 * Success closes the dialog and reports through Naive's message API: a new or re-enabled
 * block as a success, an address already blocked as information, and each warning (a
 * shared exit, a wide range) as its own warning, left up longer so it can be read.
 * A failure stays in the dialog, with the reason's hint, so the analyst can see why.
 */
async function submit() {
	if (!wafId.value) return
	const id = wafId.value
	submitting.value = true
	try {
		const { data } = await Api.customerWaf.block(props.customerCode, id, {
			target: target.value.trim(),
			reason: reason.value.trim(),
			alert_id: props.alertId
		})
		const fresh = data.action === "created" || data.action === "reenabled"
		if (fresh) message.success(data.message)
		else message.info(data.message)
		for (const warning of data.warnings ?? []) message.warning(warning, { duration: 8000 })
		emit("blocked", { wafId: id, action: data.action, target: data.target })
		show.value = false
	} catch (err) {
		const reasonCode = ((err as ApiError).response?.data as { reason?: string } | undefined)?.reason
		const hint = reasonHint(reasonCode)
		result.value = {
			type: "error",
			message: getApiErrorMessage(err as ApiError) || "Blocking failed.",
			warnings: hint ? [hint] : []
		}
	} finally {
		submitting.value = false
	}
}
</script>
