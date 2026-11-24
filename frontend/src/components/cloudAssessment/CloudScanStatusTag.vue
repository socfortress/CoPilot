<template>
	<!-- A state is an icon and a word, never a colour alone. -->
	<n-tag :type="SCAN_STATUS_TAGS[status]" size="small" round :bordered="false" data-testid="cloud-scan-status">
		<template #icon>
			<Icon :name="SCAN_STATUS_ICONS[status]" :size="12" :class="{ 'animate-spin': spinning }" />
		</template>
		{{ SCAN_STATUS_LABELS[status] }}
	</n-tag>
</template>

<script setup lang="ts">
import type { CloudScanStatus } from "@/types/cloud-assessment"
import { NTag } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { SCAN_STATUS_ICONS, SCAN_STATUS_LABELS, SCAN_STATUS_TAGS } from "./utils"

const { status } = defineProps<{ status: CloudScanStatus }>()

const spinning = computed(() => status === "starting" || status === "running" || status === "ingesting")
</script>
