<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Spin</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/spin"
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
			<CardCodeExample title="Basic">
				<template #description>
					Here are
					<n-text code>small</n-text>
					,
					<n-text code>medium</n-text>
					and
					<n-text code>large</n-text>
					spins.
				</template>
				<n-space>
					<n-spin size="small" />
					<n-spin size="medium" />
					<n-spin size="large" />
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space>
						<n-spin size="small" />
						<n-spin size="medium" />
						<n-spin size="large" />
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Wrap">
				<template #description>You can wrap a component inside spin.</template>
				<n-space vertical>
					<n-spin :show="show">
						<n-alert title="La La La" type="success">
							Leave it till tomorrow to unpack my case. Honey disconnect the phone.
						</n-alert>
					</n-spin>
					<n-button @click="show = !show">Click to Spin</n-button>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-spin :show="show">
							<n-alert title="La La La" type="success">
								Leave it till tomorrow to unpack my case. Honey disconnect the phone.
							</n-alert>
						</n-spin>
						<n-button @click="show = !show">Click to Spin</n-button>
					</n-space>
					`) }}

					{{ js(`const show = ref(false)`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NText, NSpin, NButton, NAlert } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const show = ref(false)
</script>
