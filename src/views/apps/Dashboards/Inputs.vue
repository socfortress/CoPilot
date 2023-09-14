<template>
    <el-scrollbar class="page page-inputs">
        <div class="section">
            <InputsMarquee :inputs="runningInputs" @click="setInput" />
        </div>

        <div class="section">
            <Details :inputs="configuredInputs" v-model="currentInput" />
        </div>

    </el-scrollbar>
</template>

<script lang="ts" setup>
import { RunningInput, ConfiguredInput } from "@/types/graylog.d"
import Api from "@/api"
import { ElMessage } from "element-plus"
import { onBeforeMount, ref } from "vue"
import InputsMarquee from "@/components/inputs/Marquee.vue"
import Details from "@/components/inputs/Details.vue"

const runningInputs = ref<RunningInput[] | null>(null)
const configuredInputs = ref<ConfiguredInput[] | null>(null)
const loadingInput = ref(false)
const currentInput = ref<RunningInput | null>(null)

function setInput(input: RunningInput) {
    currentInput.value = input
}

function getInputsRunning() {
    loadingInput.value = true

    Api.graylog
        .getInputsRunning()
        .then(res => {
            if (res.data.running_inputs.success) {
              runningInputs.value = res.data.running_inputs.inputs
            } else {
                ElMessage({
                    message: res.data.running_inputs?.message || "An error occurred. Please try again later.",
                    type: "error"
                })
            }
        })
        .catch(err => {
            // Handle errors
        })
        .finally(() => {
            loadingInput.value = false
        })
}

function getInputsConfigured() {
    loadingInput.value = true

    Api.graylog
        .getInputsConfigured()
        .then(res => {
            if (res.data.configured_inputs.success) {
              configuredInputs.value = res.data.configured_inputs.configured_inputs
            } else {
                ElMessage({
                    message: res.data.configured_inputs?.message || "An error occurred. Please try again later.",
                    type: "error"
                })
            }
        })
        .catch(err => {
            // Handle errors
        })
        .finally(() => {
            loadingInput.value = false
        })
}

onBeforeMount(() => {
  getInputsRunning(),
  getInputsConfigured()
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.page-inputs {
    .section {
        margin-bottom: var(--size-6);
        .columns {
            display: flex;
            gap: var(--size-6);

            .col {
                flex-grow: 1;
                overflow: hidden;
                &.basis-20 {
                    flex-basis: 20%;
                }
                &.basis-40 {
                    flex-basis: 40%;
                }
                &.basis-50 {
                    flex-basis: 50%;
                }
                &.basis-60 {
                    flex-basis: 60%;
                }
                &.basis-80 {
                    flex-basis: 80%;
                }
            }

            .stretchy {
                height: 100%;
                box-sizing: border-box;
            }
        }
    }

    @media (max-width: 1000px) {
        .section {
            .columns {
                flex-direction: column;
            }
        }
    }
    @media (max-width: 1200px) {
        .section {
            .columns.column-1200 {
                flex-direction: column;
            }
        }
    }
}
</style>
