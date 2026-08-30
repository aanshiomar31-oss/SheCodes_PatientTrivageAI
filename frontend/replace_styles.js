const fs = require('fs');
const path = require('path');
const glob = require('glob');

const dir = path.join(__dirname, 'src');

const replacements = [
  [/rounded-2xl border border-slate-700\/50 bg-white\/5 backdrop-blur-md/g, 'panel'],
  [/rounded-2xl border border-slate-700\/50 bg-white\/5 p-6 backdrop-blur-md/g, 'panel p-6'],
  [/rounded-2xl border border-slate-700\/50 bg-white\/5 p-5 backdrop-blur-md/g, 'panel p-5'],
  [/rounded-2xl border border-slate-700\/50 bg-white\/5 p-4 backdrop-blur-md/g, 'panel p-4'],
  [/rounded-xl border border-slate-700\/50 bg-white\/5 p-6 backdrop-blur-sm/g, 'panel p-6'],
  [/rounded-xl border border-slate-700\/50 bg-white\/5 backdrop-blur-sm/g, 'panel'],
  [/text-slate-100/g, 'text-surface-ink'],
  [/text-slate-200/g, 'text-surface-ink'],
  [/text-slate-300/g, 'text-slate-600'],
  [/text-slate-400/g, 'text-surface-muted'],
  [/text-slate-500/g, 'text-surface-muted']
];

function processDir(dirPath) {
  const files = fs.readdirSync(dirPath);
  for (const file of files) {
    const fullPath = path.join(dirPath, file);
    if (fs.statSync(fullPath).isDirectory()) {
      processDir(fullPath);
    } else if (fullPath.endsWith('.jsx') || fullPath.endsWith('.js')) {
      let content = fs.readFileSync(fullPath, 'utf8');
      if (content.includes('border-slate-700/50 bg-white/5') || content.includes('text-slate-')) {
        let originalContent = content;
        for (const [regex, replacement] of replacements) {
          content = content.replace(regex, replacement);
        }
        if (content !== originalContent) {
          fs.writeFileSync(fullPath, content, 'utf8');
          console.log('Updated', fullPath);
        }
      }
    }
  }
}

processDir(dir);
