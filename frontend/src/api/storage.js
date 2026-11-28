import http from './http'

export const listFiles = (params) => http.get('/storage/files', { params })

export const downloadAsset = (id, params) => http.get(`/storage/files/${id}/download`, { params, responseType: 'blob' })

export const listAlgorithms = (params) => http.get('/algorithms', { params })

export const getConfig = () => http.get('/config')

export const saveConfig = (items) => http.put('/config', { items })

export const deleteModel = (name) => http.delete(`/models/${name}`)
