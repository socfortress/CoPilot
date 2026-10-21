<template>
	<n-modal
		v-model:show="show"
		preset="card"
		:title
		class="max-w-120!"
		:mask-closable="false"
		data-testid="temporary-password-dialog"
	>
		<div class="flex flex-col gap-4">
			<template v-if="delivery?.delivery === 'shown' && delivery.temporary_password">
				<n-alert type="warning" :bordered="false" class="text-sm">
					This password is shown once. Give it to
					<b>{{ username }}</b>
					<span>{{ delivery.email_problem ? ` yourself: ${problemText}` : " yourself." }}</span>
					They choose their own at their first sign-in.
				</n-alert>
				<div class="border-default bg-secondary flex items-center gap-2 rounded-lg border px-3 py-2">
					<code
						class="text-default grow font-mono text-base break-all"
						data-testid="temporary-password-value"
					>
						{{ delivery.temporary_password }}
					</code>
					<n-button size="small" secondary data-testid="temporary-password-copy" @click="copyPassword()">
						<template #icon>
							<Icon :name="copied ? 'carbon:checkmark' : 'carbon:copy'" :size="14" />
						</template>
						{{ copied ? "Copied" : "Copy" }}
					</n-button>
				</div>
			</template>
			<p v-else class="text-secondary m-0 text-sm" data-testid="temporary-password-emailed">
				A temporary password was emailed to
				<b>{{ email }}</b>
				<span>. {{ username }} chooses their own at their first sign-in.</span>
			</p>
			<div class="flex justify-end">
				<n-button type="primary" data-testid="temporary-password-done" @click="show = false">Done</n-button>
			</div>
		</div>
	</n-modal>
</template>

<script setup lang="ts">
import type { TemporaryPasswordDelivery } from "@/types/users"
import { useClipboard } from "@vueuse/core"
import { NAlert, NButton, NModal } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

/**
 * How a temporary password reached its user (#1296): emailed, or here, once. The password is
 * never kept: it lives in the parent's state only until this dialog closes.
 */

const {
	username,
	email,
	delivery,
	invited = false
} = defineProps<{
	username: string
	email: string
	delivery: TemporaryPasswordDelivery | null
	invited?: boolean
}>()
const show = defineModel<boolean>("show", { required: true })

const { copy, copied } = useClipboard({ legacy: true })

const title = computed(() => (invited ? `${username} was invited` : `A temporary password for ${username}`))
const problemText = computed(() => {
	const problem = delivery?.email_problem ?? ""
	return problem ? `${problem.charAt(0).toLowerCase()}${problem.slice(1)}.` : ""
})

function copyPassword() {
	if (delivery?.temporary_password) copy(delivery.temporary_password)
}
</script>
