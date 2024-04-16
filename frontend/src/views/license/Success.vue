<template>
	<div class="page grow flex flex-col justify-center items-center">
		<LicenseCheckoutResponse class="max-w-96" type="success" :data="{ email: route.query.email?.toString() }" />
	</div>
</template>
<script setup lang="ts">
import { useRoute } from "vue-router"
import LicenseCheckoutResponse from "@/components/license/LicenseCheckoutResponse.vue"

const route = useRoute()
</script>
