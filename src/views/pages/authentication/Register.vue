<template>
    <el-scrollbar class="register-page">
        <div class="align-vertical">
            <div class="form-wrapper align-vertical-middle">
                <div class="form-box card-base card-shadow--extraLarge">
                    <img class="image-logo" src="@/assets/images/logo.svg" alt="logo" />

                    <div class="field-box">
                        <input type="text" placeholder="Name" />
                    </div>
                    <div class="field-box">
                        <input type="email" placeholder="E-mail" />
                    </div>
                    <div class="field-box">
                        <input type="password" placeholder="Password" />
                    </div>
                    <div class="field-box">
                        <input type="password" placeholder="Password (confirm)" />
                    </div>

                    <div class="flex">
                        <div class="box grow"><el-checkbox>I read and accept terms</el-checkbox></div>
                    </div>

                    <div>
                        <button @click="login" class="signin-btn">SIGN IN</button>
                    </div>

                    <div class="text-center login-box pt-10">Already have an account? <a>Login</a></div>
                </div>
            </div>
        </div>
    </el-scrollbar>
</template>

<script>
import { useMainStore } from "@/stores/main"
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "Register",
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

.register-page {
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

        .signin-btn {
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

        .login-box {
            font-size: 14px;
        }
    }
}

@media (max-width: 768px) {
    .layout-container .container .view.register-page {
        margin-left: -5px;
        margin-right: -5px;
        max-width: calc(100% + 10px);
    }
}
</style>
