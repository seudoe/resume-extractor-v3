// Push GitHub Actions repo secrets from .env.repo (HF_* variables) to GitHub repository.
// Usage: node scripts/push-repo-secrets.mjs [--dry]
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = resolve(import.meta.dirname, "..");
const REPO = process.env.GH_REPO ?? "seudoe/resume-extractor-v3";
const SPECIAL = process.env.SPECIAL_ENVS ?? resolve(ROOT, ".env.repo");
const dry = process.argv.includes("--dry");

if (!existsSync(SPECIAL)) {
  console.error(`Error: ${SPECIAL} not found.`);
  process.exit(1);
}

const envContent = readFileSync(SPECIAL, "utf8");

// 1. Extract GH_TOKEN
let token = process.env.GH_TOKEN;
if (!token) {
  token = envContent.match(/^\s*GH_TOKEN\s*=\s*["']?([^"'\r\n]+)/m)?.[1];
}
for (const f of [".env", ".env.local"]) {
  if (token) break;
  try {
    token = readFileSync(resolve(ROOT, f), "utf8").match(/^\s*GH_TOKEN\s*=\s*["']?([^"'\r\n]+)/m)?.[1];
  } catch {}
}

if (!token && !dry) {
  console.error("Error: GH_TOKEN is required in .env.repo or environment");
  process.exit(1);
}

// 2. Parse secrets (HF_* variables, non-empty)
const secrets = {};
const pairs = [];
let currentPair = {};

for (const rawLine of envContent.split(/\r?\n/)) {
  const line = rawLine.trim();
  if (!line || line.startsWith("#")) continue;
  const m = line.match(/^([A-Za-z0-9_]+)\s*=\s*(.*)$/);
  if (!m) continue;

  const key = m[1].trim();
  const val = m[2].trim().replace(/^["']|["']$/g, "");
  if (!val) continue; // Skip empty values (e.g. HF_TOKEN_SEUDOE=)

  // Only consider HF secrets
  if (key.startsWith("HF_")) {
    secrets[key] = val;

    if (key.startsWith("HF_USER_")) {
      currentPair.user = val;
      currentPair.suffix = key.replace("HF_USER_", "");
    } else if (key.startsWith("HF_TOKEN_")) {
      currentPair.token = val;
      currentPair.suffix = key.replace("HF_TOKEN_", "");
    }

    if (currentPair.user && currentPair.token) {
      pairs.push({ ...currentPair });
      currentPair = {};
    }
  }
}

// 3. Ensure HF_USER_1 and HF_TOKEN_1 exist for the GitHub Actions canary job
if (pairs.length > 0) {
  pairs.forEach((p, idx) => {
    const num = idx + 1;
    if (!secrets[`HF_USER_${num}`]) {
      secrets[`HF_USER_${num}`] = p.user;
    }
    if (!secrets[`HF_TOKEN_${num}`]) {
      secrets[`HF_TOKEN_${num}`] = p.token;
    }
  });
}

const secretNames = Object.keys(secrets);
if (secretNames.length === 0) {
  console.warn("No non-empty HF_* secrets found in", SPECIAL);
  process.exit(0);
}

if (dry) {
  console.log(`[DRY RUN] Target Repo: ${REPO}`);
  for (const k of secretNames) {
    console.log(`  would set ${k} (${secrets[k].length} chars)`);
  }
  process.exit(0);
}

// 4. Load libsodium-wrappers
let sodiumModule;
try {
  sodiumModule = (await import("libsodium-wrappers")).default;
} catch {
  const fallbackPath = resolve(ROOT, "../ifind/node_modules/libsodium-wrappers/dist/modules/libsodium-wrappers.js");
  if (existsSync(fallbackPath)) {
    const mod = await import(pathToFileURL(fallbackPath).href);
    sodiumModule = mod.default;
  } else {
    console.error("Could not load libsodium-wrappers. Please install it or ensure ../ifind has it.");
    process.exit(1);
  }
}

await sodiumModule.ready;
const sodium = sodiumModule;

// 5. Query GitHub Actions Public Key
const api = (path, init = {}) =>
  fetch(`https://api.github.com/repos/${REPO}/actions/secrets${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${token}`,
      accept: "application/vnd.github+json",
      "x-github-api-version": "2022-11-28",
      ...init.headers,
    },
  });

console.log(`Fetching public key for ${REPO}...`);
const pkRes = await api("/public-key");
const pk = await pkRes.json();

if (!pk.key) {
  console.error("\n[Error] Unable to get repository public key from GitHub:");
  console.error(JSON.stringify(pk, null, 2));
  if (pk.message?.includes("Resource not accessible by personal access token")) {
    console.error(`
--------------------------------------------------------------------------------
Your Personal Access Token (GH_TOKEN) does not have access to repo: "${REPO}".

To fix this:
1. Go to GitHub: https://github.com/settings/tokens
2. Under "Fine-grained tokens", click your token.
3. In "Repository access", ensure "${REPO}" is selected.
4. Under "Repository permissions", set "Secrets" to Read and Write.
5. Save changes and re-run this script.
--------------------------------------------------------------------------------`);
  }
  process.exit(1);
}

// 6. Encrypt and push each secret
console.log(`Encrypting and pushing ${secretNames.length} secrets to ${REPO}...`);
let successCount = 0;

for (const [name, value] of Object.entries(secrets)) {
  const sealed = sodium.crypto_box_seal(
    sodium.from_string(value),
    sodium.from_base64(pk.key, sodium.base64_variants.ORIGINAL)
  );

  const res = await api(`/${name}`, {
    method: "PUT",
    body: JSON.stringify({
      encrypted_value: sodium.to_base64(sealed, sodium.base64_variants.ORIGINAL),
      key_id: pk.key_id,
    }),
  });

  if (res.ok) {
    console.log(`  ✓ set ${name}`);
    successCount++;
  } else {
    const errText = await res.text();
    console.error(`  ✗ FAILED ${name} (${res.status}): ${errText}`);
  }
}

console.log(`\nDone. Pushed ${successCount}/${secretNames.length} secrets.`);
