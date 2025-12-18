#!/usr/bin/env node
/**
 * Check if generated TypeScript types are up-to-date with OpenAPI spec.
 *
 * Compares SHA256 hash of openapi.json with hash stored in generated-types.ts.
 * Exits with code 1 if types need regeneration.
 *
 * Usage:
 *   npm run check:types-fresh
 *   # Or during pre-commit:
 *   node scripts/check-types-fresh.js
 */

import { createHash } from 'crypto';
import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = join(__dirname, '..');
const OPENAPI_PATH = join(ROOT_DIR, '..', 'openapi.json');
const GENERATED_PATH = join(ROOT_DIR, 'src', 'lib', 'api', 'generated-types.ts');
const HASH_FILE_PATH = join(ROOT_DIR, 'src', 'lib', 'api', '.openapi-hash');

function computeHash(content) {
	return createHash('sha256').update(content).digest('hex').substring(0, 16);
}

function main() {
	// Check if openapi.json exists
	if (!existsSync(OPENAPI_PATH)) {
		console.log('⏭️  openapi.json not found - skipping freshness check');
		console.log('   Run `make openapi-export` to generate it');
		process.exit(0);
	}

	// Check if generated-types.ts exists
	if (!existsSync(GENERATED_PATH)) {
		console.error('❌ generated-types.ts not found');
		console.error('   Run `npm run generate:types` to generate it');
		process.exit(1);
	}

	// Compute current hash of openapi.json
	const openapiContent = readFileSync(OPENAPI_PATH, 'utf-8');
	const currentHash = computeHash(openapiContent);

	// Read stored hash (if exists)
	let storedHash = null;
	if (existsSync(HASH_FILE_PATH)) {
		storedHash = readFileSync(HASH_FILE_PATH, 'utf-8').trim();
	}

	// Compare
	if (storedHash === currentHash) {
		console.log('✅ Generated types are up-to-date with OpenAPI spec');
		process.exit(0);
	}

	// Types are stale
	console.error('❌ Generated types are out of date with OpenAPI spec');
	console.error(`   OpenAPI hash: ${currentHash}`);
	console.error(`   Stored hash:  ${storedHash || '(none)'}`);
	console.error('');
	console.error('   To regenerate: npm run generate:types');
	console.error('   Or run: make generate-types');
	process.exit(1);
}

main();
