<template>
	<n-card hoverable content-style="padding: 0;">
		<div class="flex xs:flex-row flex-col xs:items-stretch">
			<div class="basis-3/5 flex flex-col">
				<div class="card-header flex justify-between items-center">
					<div>
						<span>
							{{ title }}
						</span>
					</div>
				</div>
				<div class="card-content grow">
					<div class="mb-3">
						<n-rate readonly :allow-half="true" :default-value="5" color="#FFB600" />
					</div>
					<p v-html="text"></p>
					<div class="divider"></div>
					<div class="features flex justify-around">
						<Icon :size="20" :name="CheckIcon"></Icon>
						<Icon :size="20" :name="StarIcon"></Icon>
						<Icon :size="20" :name="ShieldIcon"></Icon>
						<Icon :size="20" :name="PremiumIcon"></Icon>
						<Icon :size="20" :name="EcoIcon"></Icon>
					</div>
				</div>
			</div>
			<div class="card-info basis-2/5 flex flex-col justify-between items-center">
				<div class="mb-4">
					<n-radio-group v-model:value="subscription" name="subscription">
						<n-radio-button value="monthly" label="Monthly" />
						<n-radio-button value="yearly" label="Yearly" />
					</n-radio-group>
				</div>
				<div class="text-xl mb-4">
					<div v-if="subscription === 'monthly'">
						<strong>$29</strong>
						<span>/month</span>
					</div>
					<div v-if="subscription === 'yearly'">
						<strong>$299</strong>
						<span>/year</span>
						<br />
						<small class="opacity-60">$24,90/month</small>
					</div>
				</div>
				<n-button type="primary">
					<Icon class="mr-3" :name="PremiumIcon"></Icon>
					Subscribe now
				</n-button>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { faker } from "@faker-js/faker"
import { NCard, NButton, NRate, NRadioGroup, NRadioButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { ref } from "vue"

const CheckIcon = "fluent:checkmark-starburst-16-regular"
const StarIcon = "fluent:star-16-regular"
const ShieldIcon = "fluent:shield-keyhole-16-regular"
const PremiumIcon = "fluent:premium-24-regular"
const EcoIcon = "material-symbols:eco-outline"

const subscription = ref("monthly")

const title = faker.lorem.sentence({ min: 2, max: 4 })
const text = faker.lorem.sentences(2, "<br/><br/>") + faker.lorem.paragraph()
</script>

<style scoped lang="scss">
.n-card {
	overflow: hidden;

	.card-header {
		box-sizing: border-box;
		display: flex;
		align-items: center;
		font-weight: 700;
		font-family: var(--font-family-display);
		font-size: var(--n-title-font-size);
		padding: var(--n-padding-top) var(--n-padding-left) var(--n-padding-bottom) var(--n-padding-left);
	}

	.card-content {
		box-sizing: border-box;
		padding: 0 var(--n-padding-left) var(--n-padding-bottom) var(--n-padding-left);
		font-size: var(--n-font-size);
	}

	.card-info {
		box-sizing: border-box;
		transition:
			background-color 0.3s var(--n-bezier),
			border-color 0.3s var(--n-bezier);
		background-clip: padding-box;
		background-color: var(--n-action-color);
		padding: var(--n-padding-bottom) var(--n-padding-left);
	}

	.divider {
		background-color: var(--border-color);
		margin: 20px 0;
		margin-left: calc(var(--n-padding-left) * -1);
		margin-right: calc(var(--n-padding-left) * -1);
		height: 1px;
	}
}
</style>
