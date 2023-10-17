<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Skeleton</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/skeleton"
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
				<n-skeleton text :repeat="2" />
				<n-skeleton text style="width: 60%" />
				<template #code="{ html }">
					{{ html(`
					<n-skeleton text :repeat="2" />
					<n-skeleton text style="width: 60%" />
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Box">
				<n-space vertical>
					<n-skeleton height="40px" width="33%" />
					<n-skeleton height="40px" width="66%" :sharp="false" />
					<n-skeleton height="40px" round />
					<n-skeleton height="40px" circle />
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space vertical>
						<n-skeleton height="40px" width="33%" />
						<n-skeleton height="40px" width="66%" :sharp="false" />
						<n-skeleton height="40px" round />
						<n-skeleton height="40px" circle />
					</n-space>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Size">
				<n-space vertical>
					<n-space>
						<n-switch v-model:value="loading" />
						Loading
					</n-space>
					<n-space>
						<n-skeleton v-if="loading" :width="146" :sharp="false" size="medium" />
						<n-button v-else>Won't you fly high</n-button>
						<n-skeleton v-if="loading" :width="132" round size="medium" />
						<n-button v-else round>free bird, yeah</n-button>
						<n-skeleton v-if="loading" circle size="medium" />
						<n-button v-else circle>?</n-button>
					</n-space>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-space>
							<n-switch v-model:value="loading" />
							Loading
						</n-space>
						<n-space>
							<n-skeleton v-if="loading" :width="146" :sharp="false" size="medium" />
							<n-button v-else>Won't you fly high</n-button>
							<n-skeleton v-if="loading" :width="132" round size="medium" />
							<n-button v-else round>free bird, yeah</n-button>
							<n-skeleton v-if="loading" circle size="medium" />
							<n-button v-else circle>?</n-button>
						</n-space>
					</n-space>
					`) }}

					{{ js(`const loading = ref(true)`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NSwitch, NSkeleton, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const loading = ref(true)
</script>
