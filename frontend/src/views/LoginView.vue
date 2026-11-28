<template>
  <div class="login-page">
    <div class="ambient one" />
    <div class="ambient two" />
    <div class="login-grid">
      <section class="intro">
        <div class="brand">
          <div class="brand-mark">J</div>
          <span>JIT 缺陷预测</span>
        </div>
        <h1>在提交发生前，<br />看见缺陷风险。</h1>
        <p class="lead">
          从仓库收集、数据清洗，到模型训练、预测与评估，一条完整的即时缺陷预测工作流。
        </p>
        <div class="feature-list">
          <div class="feature"><span>01</span> 状态流转可追踪</div>
          <div class="feature"><span>02</span> 专家与语义双模型线</div>
          <div class="feature"><span>03</span> 解释与缺陷定位</div>
        </div>
      </section>

      <section class="card">
        <div class="card-head">
          <h2>登录</h2>
          <p>使用课程演示账号进入系统</p>
        </div>
        <el-form @submit.prevent="submit">
          <el-form-item label="用户名">
            <el-input
              ref="usernameRef"
              v-model="username"
              placeholder="请输入用户名"
              size="large"
              autocomplete="username"
              :disabled="loading"
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="password"
              type="password"
              show-password
              placeholder="请输入密码"
              size="large"
              autocomplete="current-password"
              :disabled="loading"
              @keyup.enter="submit"
            />
          </el-form-item>
          <div v-if="error" class="error" role="alert">{{ error }}</div>
          <el-button
            class="submit"
            type="primary"
            size="large"
            native-type="submit"
            :loading="loading"
            :disabled="!canSubmit"
          >
            登录
          </el-button>
        </el-form>
        <p class="footnote">账号由管理员通过命令行创建，不提供注册与找回密码。</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { humanError } from '../utils/format'
import { signIn } from '../stores/session'

const route = useRoute()
const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const usernameRef = ref(null)

const canSubmit = computed(() => username.value.trim() && password.value && !loading.value)

onMounted(() => nextTick(() => usernameRef.value?.focus()))

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  error.value = ''
  try {
    await signIn(username.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/storage'
    await router.replace(redirect)
  } catch (requestError) {
    error.value = requestError.status === 0 ? '无法连接服务器，请重试' : humanError(requestError)
    password.value = ''
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 40px 24px;
  overflow: hidden;
  background: #071019;
}

.ambient {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.55;
}

.ambient.one {
  width: 520px;
  height: 520px;
  background: radial-gradient(circle, rgba(45, 212, 191, 0.5), transparent 65%);
  top: -160px;
  right: -80px;
}

.ambient.two {
  width: 480px;
  height: 480px;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.42), transparent 65%);
  bottom: -180px;
  left: -120px;
}

.login-grid {
  position: relative;
  width: min(1040px, 100%);
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 56px;
  align-items: center;
}

.intro {
  color: #e2e8f0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #f8fafc;
  margin-bottom: 30px;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  font-weight: 800;
  color: #06201d;
  background: linear-gradient(135deg, #5eead4, #34d399);
}

.intro h1 {
  font-size: clamp(30px, 4vw, 46px);
  line-height: 1.16;
  letter-spacing: -0.03em;
  font-weight: 780;
  color: #f8fafc;
}

.lead {
  margin-top: 18px;
  color: rgba(203, 213, 225, 0.8);
  font-size: 14.5px;
  line-height: 1.8;
  max-width: 430px;
}

.feature-list {
  margin-top: 30px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feature {
  display: flex;
  align-items: center;
  gap: 12px;
  color: rgba(226, 232, 240, 0.86);
  font-size: 13.5px;
}

.feature span {
  font-family: var(--mono);
  font-size: 11px;
  color: #5eead4;
  border: 1px solid rgba(94, 234, 212, 0.28);
  background: rgba(94, 234, 212, 0.08);
  padding: 3px 7px;
  border-radius: 7px;
}

.card {
  background: rgba(255, 255, 255, 0.98);
  border-radius: 22px;
  padding: 34px 32px 26px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.38);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.card-head h2 {
  font-size: 22px;
  letter-spacing: -0.02em;
}

.card-head p {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 12.5px;
  margin-bottom: 22px;
}

.error {
  margin-bottom: 14px;
  padding: 9px 12px;
  border-radius: 9px;
  background: var(--danger-soft);
  color: #7f1d1d;
  font-size: 12.5px;
  border: 1px solid rgba(214, 69, 69, 0.18);
}

.submit {
  width: 100%;
  margin-top: 4px;
  height: 44px;
  font-size: 15px;
}

.footnote {
  margin-top: 20px;
  font-size: 11.5px;
  color: var(--text-soft);
  line-height: 1.6;
  text-align: center;
}

@media (max-width: 900px) {
  .login-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 28px;
  }

  .intro h1 {
    font-size: 28px;
  }

  .feature-list {
    display: none;
  }
}

@media (max-width: 768px) {
  .login-page {
    padding: 22px 16px;
  }

  .intro {
    text-align: center;
  }

  .brand {
    justify-content: center;
  }

  .lead {
    margin-left: auto;
    margin-right: auto;
  }

  .card {
    padding: 26px 20px 20px;
  }
}
</style>
