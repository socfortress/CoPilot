<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Milkdown</div>
			<div class="links">
				<a
					href="https://milkdown.dev/"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
					class="ml-4"
				>
					<n-icon :size="16">
						<ExternalIcon />
					</n-icon>
					docs
				</a>
			</div>
		</div>

		<n-card><Milkdown /></n-card>
	</div>
</template>

<script setup lang="ts">
import { NIcon, NCard } from "naive-ui"
import ExternalIcon from "@vicons/tabler/ExternalLink"
import Milkdown from "@/components/editors/Milkdown"
</script>
