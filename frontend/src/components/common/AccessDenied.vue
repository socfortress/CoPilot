<template>
	<div class="flex min-h-[60vh] items-center justify-center">
		<n-result
			status="403"
			title="Access Denied"
			:description="description || 'You do not have permission to view this page.'"
		>
			<template #footer>
				<n-space justify="center">
					<n-button type="primary" @click="goBack">
						<template #icon>
							<Icon name="carbon:arrow-left" />
						</template>
						Go Back
					</n-button>
					<n-button @click="goHome">
						<template #icon>
							<Icon name="carbon:home" />
						</template>
						Go to Dashboard
					</n-button>
				</n-space>
			</template>
		</n-result>
	</div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"

interface Props {
	description?: string
}

defineProps<Props>()

const router = useRouter()

function goBack() {
	router.back()
}

function goHome() {
	router.push("/")
}
</script>
