<template>
	<n-dropdown trigger="click" placement="bottom-end" :options="actions" @select="confirmArchive">
		<n-button
			size="tiny"
			quaternary
			circle
			:aria-label="$t('talonChat.threads.actionsNamed', { title: threadTitle(thread) })"
			:title="$t('talonChat.threads.actionsNamed', { title: threadTitle(thread) })"
			:disabled
			v-bind="$attrs"
		>
			<template #icon><Icon name="carbon:overflow-menu-horizontal" /></template>
		</n-button>
	</n-dropdown>
</template>

<script setup lang="ts">
import type { DropdownOption } from "naive-ui"
import type { TalonChatThread } from "@/types/talonChat"
import { NButton, NDropdown, useDialog } from "naive-ui"
import { computed, h } from "vue"
import { useI18n } from "vue-i18n"
import Icon from "@/components/common/Icon.vue"
import { threadTitle } from "./talonChat"

/**
 * A conversation's actions ("…"), in its inbox row and above the open conversation: closing it,
 * once confirmed. The API offers no other action on a thread (no rename).
 */
defineOptions({ inheritAttrs: false })

const { thread, disabled = false } = defineProps<{ thread: TalonChatThread; disabled?: boolean }>()

const emit = defineEmits<{ archive: [id: string] }>()

const { t } = useI18n()
const dialog = useDialog()

const actions = computed<DropdownOption[]>(() => [
	{ key: "archive", label: t("talonChat.threads.archive"), icon: () => h(Icon, { name: "carbon:archive" }) }
])

function confirmArchive() {
	dialog.warning({
		title: t("talonChat.threads.archiveNamed", { title: threadTitle(thread) }),
		content: t("talonChat.threads.archiveConfirm"),
		positiveText: t("talonChat.threads.archive"),
		negativeText: t("common.actions.cancel"),
		onPositiveClick: () => {
			emit("archive", thread.id)
		}
	})
}
</script>
