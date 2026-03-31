<template>
	<div class="flex flex-col gap-2">
		<n-alert type="info">Backup codes generated. Save them — they are shown only once.</n-alert>

		<div class="grid max-w-140 grid-cols-2 gap-2">
			<n-code v-for="code in codes" :key="code" class="p-2 text-center">
				{{ code }}
			</n-code>
		</div>

		<div class="flex gap-2">
			<n-button v-if="isCopySupported" size="small" secondary @click="copyBackupCodes(codes)">
				<template #icon>
					<Icon name="carbon:copy" />
				</template>
				Copy all
			</n-button>
			<n-button size="small" secondary @click="downloadBackupCodes(codes)">
				<template #icon>
					<Icon name="carbon:download" />
				</template>
				Download .txt
			</n-button>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { useClipboard } from "@vueuse/core"
import { saveAs } from "file-saver"
import { NAlert, NButton, NCode, useMessage } from "naive-ui"
import { watch } from "vue"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	codes: string[]
}>()

const message = useMessage()
const { copy, copied, isSupported: isCopySupported } = useClipboard()

function copyBackupCodes(codes: string[]) {
	copy(codes.join("\n"))
}

function downloadBackupCodes(codes: string[]) {
	const text = `CoPilot — 2FA Backup Codes\n${"=".repeat(30)}\n\n${codes.join(
		"\n"
	)}\n\nKeep these codes safe. Each code can only be used once.\n`

	saveAs(new Blob([text], { type: "text/plain" }), "copilot-2fa-backup-codes.txt")
}

watch(copied, newVal => {
	if (newVal) {
		message.success("Backup codes copied to clipboard")
	}
})
</script>
