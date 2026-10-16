import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * 全局"识别整卷"任务表：按 PDF 内部名（name）独立跟踪，跨页面/组件保持显示。
 * 解决：切换页面或上传新 PDF 后，原识别任务消失、按钮又可重复点击的问题。
 */
export const useRecognitionStore = defineStore('recognition', () => {
  const tasks = ref({}) // name -> startedAt(ms)

  function start(name) {
    if (!name || tasks.value[name]) return
    tasks.value[name] = Date.now()
  }
  function finish(name) {
    if (name) delete tasks.value[name]
  }
  function isRunning(name) {
    return !!name && !!tasks.value[name]
  }
  const runningNames = computed(() => Object.keys(tasks.value))
  const runningCount = computed(() => runningNames.value.length)

  return { tasks, start, finish, isRunning, runningNames, runningCount }
})