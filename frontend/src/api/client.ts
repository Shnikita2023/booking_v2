import axios from 'axios';
import { attachInterceptors } from './interceptor';

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

attachInterceptors(client);

export default client;
