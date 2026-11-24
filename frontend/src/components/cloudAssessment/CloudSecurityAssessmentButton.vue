<template>
	<n-button :size :type :secondary @click="gotoPage()">
		<template #icon>
			<Icon :name="CloudIcon" />
		</template>
		Cloud Security Assessment
	</n-button>
</template>

<script setup lang="ts">
import type { ButtonSize, ButtonType } from "naive-ui"
import { NButton } from "naive-ui"
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"

defineProps<{
	size?: ButtonSize
	type?: ButtonType
	secondary?: boolean
}>()

const CloudIcon = "carbon:cloud-data-ops"

const router = useRouter()

function gotoPage() {
	router.push({ name: "CloudSecurityAssessment" })
}
</script>
