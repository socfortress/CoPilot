<template>
	<n-button :size="size" :type="type" @click="gotoPage()">
		<template #icon>
			<Icon :name="CloudIcon" />
		</template>
		Cloud Security Assessment
	</n-button>
</template>

<script setup lang="ts">
import type { Size, Type } from "naive-ui/es/button/src/interface"
import { NButton } from "naive-ui"
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"

const { type, size } = defineProps<{
	size?: Size
	type?: Type
}>()

const CloudIcon = "carbon:cloud-data-ops"

const router = useRouter()

function gotoPage() {
	router.push({ name: "CloudSecurityAssessment" })
}
</script>
