#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
try {
  fs.copyFileSync(path.join('public', 'index.html'), 'index.html');
} catch (e) {}
try {
  fs.copyFileSync(path.join('public', 'model.glb'), 'model.glb');
} catch (e) {}
require('child_process').spawnSync('npx', ['serve', '.', '--single', '--listen', '3000'], {
  stdio: 'inherit',
  shell: true
});
