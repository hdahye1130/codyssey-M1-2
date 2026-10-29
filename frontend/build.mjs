import { mkdirSync, copyFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
mkdirSync('dist', { recursive: true });
for (const file of ['index.html', 'style.css', 'app.js']) copyFileSync(file, join('dist', file));
const url = process.env.API_SERVER_URL || 'http://localhost:8000';
if (!/^https?:\/\//.test(url)) throw new Error('API_SERVER_URL must start with http:// or https://');
writeFileSync('dist/config.js', 'window.SOLAR_API_URL = ' + JSON.stringify(url) + ';\n');
console.log('Built vanilla frontend. API server: ' + url);
