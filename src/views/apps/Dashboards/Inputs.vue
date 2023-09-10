<template>
  <el-scrollbar class="page page-inputs">
    <div class="section">
      <InputsMarquee :inputs="inputs" @click="setInput" />
    </div>
  </el-scrollbar>
</template>

<script lang="ts" setup>
import { RunningInput } from "@/types/graylog.d";
import Api from "@/api";
import { ElMessage } from "element-plus";
import { onBeforeMount, ref } from "vue";
import InputsMarquee from "@/components/inputs/Marquee.vue";

const inputs = ref<RunningInput[] | null>(null);
const loadingInput = ref(false);
const currentInput = ref<RunningInput | null>(null);

function setInput(input: RunningInput) {
  currentInput.value = input;
}

function getInputs() {
  loadingInput.value = true;

  Api.graylog
    .getInputs()
    .then(res => {
      if (res.data.running_inputs.success) {
        inputs.value = res.data.running_inputs.inputs;
      } else {
        ElMessage({
          message: res.data.running_inputs?.message || "An error occurred. Please try again later.",
          type: "error"
        });
      }
    })
    .catch(err => {
      // Handle errors
    })
    .finally(() => {
      loadingInput.value = false;
    });
}

onBeforeMount(() => {
  getInputs();
});
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
