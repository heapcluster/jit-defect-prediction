import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
// 组件库文案走中文（分页「共 x 条」、日期选择器、空数据提示等；
// 此前未设 locale，内置文案是英文，与 index.html 的 lang="zh-CN" 割裂）
app.use(ElementPlus, { locale: zhCn })
app.use(router)
app.mount('#app')
