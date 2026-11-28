import http from './http'

export const getPageState = (page) => http.get(`/page-state/${page}`)

export const putPageState = (page, state) => http.put(`/page-state/${page}`, state)

export const deletePageState = (page) => http.delete(`/page-state/${page}`)
