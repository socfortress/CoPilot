<template>
	<n-tabs type="line" animated :tabs-padding="24">
		<n-tab-pane name="Wazuh Rules" tab="Wazuh Rules" display-directive="show">
			<div class="p-7 pt-4">
				<CodeSource :code="wazuh_rule" lang="xml" />
			</div>
		</n-tab-pane>
		<n-tab-pane name="Explanation" tab="Explanation" display-directive="show">
			<div class="p-7 pt-4">
				<n-input
					:value="data.explanation"
					type="textarea"
					size="large"
					readonly
					placeholder="Empty"
					:autosize="{
						minRows: 3
					}"
				/>
			</div>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { WazuhRuleExclude } from "@/types/alerts.d"
import { NInput, NTabPane, NTabs } from "naive-ui"
import { computed, defineAsyncComponent, toRefs } from "vue"

const props = defineProps<{ data: WazuhRuleExclude }>()

const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const { data } = toRefs(props)

const wazuh_rule = computed(() => data.value.wazuh_rule.replace(/\\\\/g, "\\\\\\\\"))
</script>

<style lang="scss" scoped>
.scrollbar-styled {
	:deep() {
		pre {
			background-color: var(--bg-secondary-color) !important;
			border-radius: var(--border-radius);
			border: 1px solid var(--border-color);
			overflow: hidden;
		}
		code {
			background-color: transparent;
		}
	}
}
</style>
