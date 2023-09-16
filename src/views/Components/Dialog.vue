<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Dialog</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/dialog"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
					class="ml-4"
				>
					<n-icon :size="16">
						<ExternalIcon />
					</n-icon>
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic" class="max-w-lg">
				<n-space>
					<n-button @click="handleConfirm">Confirm</n-button>
					<n-button @click="handleSuccess">Success</n-button>
					<n-button @click="handleError">Error</n-button>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space>
						<n-button @click="handleConfirm">Confirm</n-button>
						<n-button @click="handleSuccess">Success</n-button>
						<n-button @click="handleError">Error</n-button>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NIcon, NSpace, NButton, useDialog, useMessage } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"

const message = useMessage()
const dialog = useDialog()

function handleConfirm() {
	dialog.warning({
		title: "Confirm",
		content: "Are you sure?",
		positiveText: "Sure",
		negativeText: "Not Sure",
		onPositiveClick: () => {
			message.success("Sure")
		},
		onNegativeClick: () => {
			message.error("Not Sure")
		}
	})
}
function handleSuccess() {
	dialog.success({
		title: "Success",
		content: "Cool",
		positiveText: "Wow!",
		onPositiveClick: () => {
			message.success("Great!")
		}
	})
}
function handleError() {
	dialog.error({
		title: "Error",
		content: "A mistake.",
		positiveText: "Ahhh!",
		onPositiveClick: () => {
			message.success("I knew it...")
		}
	})
}
</script>
