#!/usr/bin/env node
/**
 * Save SHA256 hash of openapi.json after type generation.
 * Used by check-types-fresh.js to detect stale types.
 */

import { createHash } from 'crypto';
import { readFileSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = join(__dirname, '..');
const OPENAPI_PATH = join(ROOT_DIR, '..', 'openapi.json');
const HASH_FILE_PATH = join(ROOT_DIR, 'src', 'lib', 'api', '.openapi-hash');

function main() {
	const openapiContent = readFileSync(OPENAPI_PATH, 'utf-8');
	const hash = createHash('sha256').update(openapiContent).digest('hex').substring(0, 16);

	writeFileSync(HASH_FILE_PATH, hash + '\n');
	console.log(`✓ OpenAPI hash saved: ${hash}`);
}

main();
