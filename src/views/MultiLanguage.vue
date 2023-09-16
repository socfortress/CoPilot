<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Multi Language</div>
		</div>

		Multi language support is provided by the
		<a href="https://vue-i18n.intlify.dev/" target="_blank" alt="docs" rel="nofollow noopener noreferrer">
			vue-i18n
		</a>
		plugin. For more information and to find out about all possible implementations, I invite you to read the plugin
		documentation.
		<br />
		In the
		<a href="#" target="_blank" alt="docs" rel="nofollow noopener noreferrer">template documentation</a>
		you can find out how it was implemented.

		<n-card class="demo">
			<LocaleSelect class="mb-5" />

			<p>
				{{ $t("sun_description") }}
			</p>
		</n-card>
	</div>
</template>

<script lang="ts" setup>
import { NCard } from "naive-ui"
import LocaleSelect from "@/components/common/LocaleSelect.vue"
</script>

<style lang="scss" scoped>
.page {
	.header {
		font-family: var(--font-family-display);
		margin-bottom: 20px;

		span {
			font-weight: bold;
			font-size: 30px;
		}
	}

	a {
		font-weight: 500;
	}

	.demo {
		margin-top: 24px;
	}
}
</style>
