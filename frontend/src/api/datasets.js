import http from './http'

export const listDatasets = (params) => http.get('/datasets', { params })

export const getDataset = (id, params) => http.get(`/datasets/${id}`, { params })

export const saveDataset = (jobId, name) => http.post('/datasets', { job_id: jobId, name })

export const deleteDataset = (id) => http.delete(`/datasets/${id}`)
