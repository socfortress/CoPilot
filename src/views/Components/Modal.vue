<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Modal</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/modal"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic" class="max-w-lg">
				<template #description>
					Basic usage of modal. You can put anything in modal, a card for example.
				</template>
				<n-button @click="showModal = true">Start Me up</n-button>
				<n-modal v-model:show="showModal">
					<n-card
						style="width: 600px"
						title="Modal"
						:bordered="false"
						size="huge"
						role="dialog"
						aria-modal="true"
					>
						<template #header-extra>Oops!</template>
						Content
						<template #footer>Footer</template>
					</n-card>
				</n-modal>
				<template #code="{ html, js }">
					{{ html(`
					<n-button @click="showModal = true">Start Me up</n-button>
					<n-modal v-model:show="showModal">
						<n-card
							style="width: 600px"
							title="Modal"
							:bordered="false"
							size="huge"
							role="dialog"
							aria-modal="true"
						>
							<template #header-extra>Oops!</template>
							Content
							<template #footer>Footer</template>
						</n-card>
					</n-modal>
					`) }}

					{{
						js(`
						const showModal = ref(false)
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NModal, NCard, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const showModal = ref(false)
</script>
