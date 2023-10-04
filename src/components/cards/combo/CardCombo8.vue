<template>
	<n-card>
		<div class="card-wrap flex justify-between">
			<div class="item-box">
				<CardCombo7 showPercentage>
					<template #icon>
						<n-avatar round src="/images/logo-1.png" :size="30" />
					</template>
				</CardCombo7>
			</div>
			<div class="divider">
				<div class="line"></div>
			</div>
			<div class="item-box">
				<CardCombo7 showPercentage>
					<template #icon>
						<n-avatar round src="/images/logo-2.png" :size="30" />
					</template>
				</CardCombo7>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { NCard, NAvatar } from "naive-ui"
</script>

<style scoped lang="scss">
.n-card {
	container-type: inline-size;

	.card-wrap {
		height: 100%;
		width: 100%;
		overflow: hidden;

		.item-box {
			width: calc(50% - 24px);
		}
		.divider {
			display: flex;
			flex-direction: column;
			align-items: center;
			justify-content: center;
			width: 48px;

			.line {
				width: 1px;
				background-color: var(--fg-secondary-color);
				flex-grow: 1;
				opacity: 0.1;
			}
		}

		@container (max-width:500px) {
			flex-direction: column;
			gap: 30px;

			.item-box {
				width: 100%;
			}

			.divider {
				display: none;
			}
		}
	}
}
</style>
