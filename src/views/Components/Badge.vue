<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Badge</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/badge"
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
				<n-space :size="24" align="center">
					<n-badge :value="value" :max="15" :processing="processing">
						<n-avatar v-if="!raw" />
					</n-badge>
					<n-badge :value="value" dot :processing="processing">
						<n-avatar v-if="!raw" />
					</n-badge>
					<n-button-group>
						<n-button @click="value = Math.min(16, value + 1)">
							<template #icon>
								<Icon :name="Add" />
							</template>
						</n-button>
						<n-button @click="value = Math.max(0, value - 1)">
							<template #icon>
								<Icon :name="Remove" />
							</template>
						</n-button>
					</n-button-group>
					<n-checkbox v-model:checked="raw">Raw</n-checkbox>
					<n-checkbox v-model:checked="processing">Processing</n-checkbox>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space :size="24" align="center">
						<n-badge :value="value" :max="15" :processing="processing">
							<n-avatar v-if="!raw" />
						</n-badge>
						<n-badge :value="value" dot :processing="processing">
							<n-avatar v-if="!raw" />
						</n-badge>
						<n-button-group>
							<n-button @click="value = Math.min(16, value + 1)">
								<template #icon>
									<n-icon><add /></n-icon>
								</template>
							</n-button>
							<n-button @click="value = Math.max(0, value - 1)">
								<template #icon>
									<n-icon><remove /></n-icon>
								</template>
							</n-button>
						</n-button-group>
						<n-checkbox v-model:checked="raw">Raw</n-checkbox>
						<n-checkbox v-model:checked="processing">Processing</n-checkbox>
					</n-space>
					`) }}

					{{
						js(`
						import { Add, Remove } from "@vicons/ionicons5"
						const value = ref(5)
						const raw = ref(false)
						const processing = ref(false)
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Type">
				<template #description>
					Badge has
					<n-text code>default</n-text>
					,
					<n-text code>error</n-text>
					,
					<n-text code>info</n-text>
					,
					<n-text code>success</n-text>
					,
					<n-text code>warning</n-text>
					types.
				</template>
				<n-space :size="24" align="center">
					<n-badge dot>
						<n-avatar />
					</n-badge>
					<n-badge dot type="error">
						<n-avatar />
					</n-badge>
					<n-badge dot type="info">
						<n-avatar />
					</n-badge>
					<n-badge dot type="success">
						<n-avatar />
					</n-badge>
					<n-badge dot type="warning">
						<n-avatar />
					</n-badge>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space :size="24" align="center">
						<n-badge dot>
							<n-avatar />
						</n-badge>
						<n-badge dot type="error">
							<n-avatar />
						</n-badge>
						<n-badge dot type="info">
							<n-avatar />
						</n-badge>
						<n-badge dot type="success">
							<n-avatar />
						</n-badge>
						<n-badge dot type="warning">
							<n-avatar />
						</n-badge>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NBadge, NAvatar, NButtonGroup, NButton, NText, NCheckbox } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const Add = "ion:add"
const Remove = "ion:remove"

const value = ref(5)
const raw = ref(false)
const processing = ref(false)
</script>
