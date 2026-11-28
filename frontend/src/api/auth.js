import http from './http'

export const fetchMe = () => http.get('/auth/me')

export const login = (username, password) => http.post('/auth/login', { username, password })

export const logout = () => http.post('/auth/logout')
