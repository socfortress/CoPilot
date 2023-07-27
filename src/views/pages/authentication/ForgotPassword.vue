<template>
    <el-scrollbar class="forgot-password-page">
        <div class="align-vertical">
            <div class="form-wrapper align-vertical-middle">
                <div class="form-box card-base card-shadow--extraLarge">
                    <img class="image-logo" src="@/assets/images/logo.svg" alt="logo" />

                    <div class="field-box">
                        <input type="email" placeholder="E-mail" />
                    </div>

                    <div class="flex text-center center pt-20 pb-10">
                        <button @click="login" class="send-btn">SEND RESET LINK</button>
                    </div>
                </div>
            </div>
        </div>
    </el-scrollbar>
</template>

<script>
import { useMainStore } from "../../../stores/main"
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "ForgotPassword",
    data() {
        return {
            form: {
                email: "",
                password: ""
            }
        }
    },
    methods: {
        login() {
            useMainStore().setLogin()
            this.$router.push("dashboard")
        }
    }
})
</script>

<style lang="scss">
@import "@/assets/scss/_variables";

.forgot-password-page {
    background: $text-color-primary;
    margin-left: -30px;
    margin-right: -30px;

    .form-wrapper {
        width: 100%;
    }

    .form-box {
        width: 100%;
        max-width: 340px;
        padding: 30px;
        box-sizing: border-box;
        margin: 20px auto;

        a {
            font-size: 14px;
            color: $text-color-accent;
            text-decoration: none;
            font-weight: 500;
        }

        .image-logo {
            width: 80px;
            margin: 0px auto;
            margin-bottom: 50px;
            display: block;
        }

        .field-box {
            margin-bottom: 10px;
            input {
                width: 100%;
                box-sizing: border-box;
                border-radius: 10px;
                padding: 10px 20px;
                outline: none;
                border: 1px solid $text-color-primary;
            }
        }

        .send-btn {
            margin-top: 20px;
            width: 100%;
            background-color: $text-color-primary;
            color: #fff;
            font-weight: bold;
            border-radius: 10px;
            padding: 10px 20px;
            outline: none;
            border: none;
        }
    }
}

@media (max-width: 768px) {
    .layout-container .container .view.forgot-password-page {
        margin-left: -5px;
        margin-right: -5px;
        max-width: calc(100% + 10px);
    }
}
</style>
