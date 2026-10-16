import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/',
  timeout: 0,
  headers: { 'Content-Type': 'application/json' }
})

request.interceptors.response.use(
  response => {
    const data = response.data
    if (data && typeof data === 'object' && 'code' in data) {
      if (data.code === 200) return data
      ElMessage.error(data.msg || '请求失败')
      const err = new Error(data.msg || '请求失败')
      err.code = data.code
      err.data = data.data
      return Promise.reject(err)
    }
    return { code: 200, data }
  },
  error => {
    const msg = (error.response && error.response.data && error.response.data.msg) || error.message
    ElMessage.error(msg || '网络错误')
    return Promise.reject(error)
  }
)

export default request
