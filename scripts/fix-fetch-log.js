#!/usr/bin/env node
/**
 * Fix fetch_log.json — converts DevTools "Copy as fetch" output to valid JSON.
 * Issues fixed:
 *   - File is JavaScript, not JSON (invalid .json)
 *   - Redundant "}); ;" → valid JSON array
 *   - Output: [{ url, method, headers, body }, ...]
 */

const fs = require('fs');
const path = require('path');

const inputPath = path.join(__dirname, '..', 'fetch_log.json');
const outputPath = path.join(__dirname, '..', 'fetch_log.json');
const backupPath = path.join(__dirname, '..', 'fetch_log.json.bak');

function extractFetchBlocks(content) {
  const entries = [];
  let i = 0;
  while (i < content.length) {
    const fetchStart = content.indexOf('fetch("', i);
    if (fetchStart === -1) break;
    const urlStart = fetchStart + 7; // len of 'fetch("'
    const urlEnd = content.indexOf('"', urlStart);
    if (urlEnd === -1) break;
    const url = content.slice(urlStart, urlEnd);
    const optsStart = content.indexOf('{', urlEnd);
    if (optsStart === -1) break;
    let depth = 0;
    let optsEnd = optsStart;
    for (let j = optsStart; j < content.length; j++) {
      if (content[j] === '{') depth++;
      else if (content[j] === '}') {
        depth--;
        if (depth === 0) { optsEnd = j; break; }
      }
    }
    const optsStr = content.slice(optsStart, optsEnd + 1);
    try {
      const opts = JSON.parse(optsStr);
      entries.push({
        url,
        method: opts.method || 'GET',
        headers: opts.headers || {},
        body: opts.body,
      });
    } catch (e) {
      console.warn('Parse skip:', url, e.message);
    }
    i = optsEnd + 1;
  }
  return entries;
}

function parseAsJson(content) {
  try {
    const data = JSON.parse(content);
    if (Array.isArray(data) && data.length > 0) {
      const first = data[0];
      if (first && typeof first.url === 'string' && (first.method || first.headers !== undefined)) {
        return data;
      }
    }
  } catch (_) {}
  return null;
}

function main() {
  const content = fs.readFileSync(inputPath, 'utf8');
  let entries = parseAsJson(content);
  const wasFetchFormat = !entries;

  if (!entries) {
    entries = extractFetchBlocks(content);
    if (entries.length === 0) {
      console.error('No fetch entries extracted. File must be either:\n  1. Valid JSON array: [{ url, method, headers?, body? }, ...]\n  2. DevTools "Copy as fetch" output');
      process.exit(1);
    }
    fs.copyFileSync(inputPath, backupPath);
    fs.writeFileSync(outputPath, JSON.stringify(entries, null, 2), 'utf8');
  }

  const uniqueUrls = [...new Set(entries.map(e => e.url))];
  const appOnly = entries.filter(e => !e.url.startsWith('chrome-extension://'));

  console.log(wasFetchFormat ? 'Fixed fetch_log.json' : 'fetch_log.json (already valid)');
  console.log('  Entries:', entries.length);
  console.log('  Unique URLs:', uniqueUrls.length);
  console.log('  App requests:', appOnly.length);
  if (wasFetchFormat) console.log('  Backup: fetch_log.json.bak');
}

main();
