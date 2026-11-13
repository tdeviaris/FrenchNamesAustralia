#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { basename, join } from 'node:path';

const ROOT = new URL('../', import.meta.url);
const rootPath = decodeURIComponent(ROOT.pathname).replace(/^\/([A-Za-z]:)/, '$1');
const dataFiles = ['baudin.json', 'entrecasteaux.json', 'flinders.json'];

const git = (...args) => execFileSync('git', args, {
  cwd: rootPath,
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe'],
});

const readDatasets = (reader) => {
  const records = new Map();
  for (const filename of dataFiles) {
    try {
      const list = JSON.parse(reader(filename));
      for (const record of list) records.set(record.code, { ...record, dataset: filename });
    } catch {
      // Un ancien commit peut précéder l'un des jeux de données.
    }
  }
  return records;
};

const current = readDatasets((filename) =>
  readFileSync(join(rootPath, 'data', filename), 'utf8'));
const sourceManifestPath = join(rootPath, 'data', 'img_sources.json');
const sourceManifest = existsSync(sourceManifestPath)
  ? JSON.parse(readFileSync(sourceManifestPath, 'utf8'))
  : {};

const imageFiles = readdirSync(join(rootPath, 'img_telecharg'))
  .filter((name) => /_Img\.jpg$/i.test(name));

const history = git('log', '--format=@@%H', '--name-only', '--', 'img_telecharg')
  .split(/\r?\n/);
const lastCommitByFile = new Map();
let commit = null;
for (const line of history) {
  if (line.startsWith('@@')) {
    commit = line.slice(2);
    continue;
  }
  const normalized = line.replace(/\\/g, '/');
  if (commit && /img_telecharg\/[^/]+_Img\.jpg$/i.test(normalized)
      && !lastCommitByFile.has(basename(normalized))) {
    lastCommitByFile.set(basename(normalized), commit);
  }
}

const recordsAtCommit = new Map();
const historicalRecords = (hash) => {
  if (!recordsAtCommit.has(hash)) {
    recordsAtCommit.set(hash, readDatasets((filename) =>
      git('show', `${hash}:data/${filename}`)));
  }
  return recordsAtCommit.get(hash);
};

const sourceKey = (value) => {
  if (!value) return '';
  let url;
  try { url = new URL(value); } catch { return value.trim().toLowerCase(); }
  let name = '';
  if (url.hostname === 'commons.wikimedia.org') {
    const page = decodeURIComponent(url.pathname).match(/\/wiki\/(?:File:|Special:Redirect\/file\/)(.+)$/i);
    if (page) name = page[1];
  } else if (url.hostname === 'upload.wikimedia.org') {
    name = decodeURIComponent(url.pathname.split('/').pop() || '');
  }
  return (name || `${url.hostname}${url.pathname}`).replace(/ /g, '_').toLowerCase();
};

const changedSources = [];
const legacyUnverified = [];
const noHistory = [];
for (const filename of imageFiles) {
  const code = filename.replace(/_Img\.jpg$/i, '');
  const hash = lastCommitByFile.get(filename);
  const now = current.get(code);
  if (!hash || !now) {
    noHistory.push({ code, file: filename, reason: !hash ? 'sans historique Git' : 'code absent des données' });
    continue;
  }
  const manifestUrl = sourceManifest[`${code}_Img`] || '';
  if (manifestUrl) {
    if (sourceKey(manifestUrl) !== sourceKey(now.imgUrl || '')) {
      changedSources.push({ code, evidence: 'manifest', oldUrl: manifestUrl, newUrl: now.imgUrl || '' });
    }
    continue;
  }

  const before = historicalRecords(hash).get(code);
  const oldUrl = before?.imgUrl || '';
  const newUrl = now.imgUrl || '';
  if (oldUrl && newUrl && sourceKey(oldUrl) !== sourceKey(newUrl)) {
    changedSources.push({ code, evidence: 'historique Git', lastImageCommit: hash.slice(0, 8), oldUrl, newUrl });
  } else {
    legacyUnverified.push({ code, lastImageCommit: hash.slice(0, 8), currentUrl: newUrl });
  }
}

const missingLocal = [];
const commonsPages = [];
for (const record of current.values()) {
  if (!record.imgUrl) continue;
  const local = join(rootPath, 'img_telecharg', `${record.code}_Img.jpg`);
  if (!existsSync(local)) missingLocal.push({ code: record.code, url: record.imgUrl });
  if (/^https:\/\/commons\.wikimedia\.org\/wiki\/(?:File:|File%3A)/i.test(record.imgUrl)) {
    commonsPages.push({ code: record.code, url: record.imgUrl });
  }
}

const report = {
  summary: {
    records: current.size,
    localImages: imageFiles.length,
    changedSources: changedSources.length,
    missingLocal: missingLocal.length,
    commonsPageUrls: commonsPages.length,
    legacyUnverified: legacyUnverified.length,
    noHistory: noHistory.length,
  },
  changedSources,
  commonsPages,
  missingLocal: process.argv.includes('--details') ? missingLocal : missingLocal.slice(0, 20),
};

if (process.argv.includes('--details')) {
  report.legacyUnverified = legacyUnverified;
  report.noHistory = noHistory;
}

console.log(JSON.stringify(report, null, 2));
