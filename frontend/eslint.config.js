import js from '@eslint/js'
import globals from 'globals'
import pluginVue from 'eslint-plugin-vue'

export default [
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**']
  },
  {
    languageOptions: {
      globals: { ...globals.browser, ...globals.node }
    }
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    rules: {
      // catch 绑定常用于保留调用栈语义或统一错误处理，不强制使用。
      'no-unused-vars': ['error', { caughtErrors: 'none', argsIgnorePattern: '^_' }]
    }
  }
]
