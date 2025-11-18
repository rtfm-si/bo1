#!/usr/bin/env node

/**
 * Generate Supabase ANON and SERVICE_ROLE keys
 *
 * Usage:
 *   node generate-supabase-keys.js YOUR_JWT_SECRET_HERE
 *
 * Example:
 *   node generate-supabase-keys.js "94AwTTzZNXRXqhDJ8rWARGgjVfX3ZUeJiJ4+ixxxa7k="
 */

const crypto = require('crypto');

// Get JWT secret from command line argument
const JWT_SECRET = process.argv[2];

if (!JWT_SECRET) {
  console.error('Error: JWT secret required');
  console.error('Usage: node generate-supabase-keys.js YOUR_JWT_SECRET');
  console.error('');
  console.error('Example:');
  console.error('  node generate-supabase-keys.js "94AwTTzZNXRXqhDJ8rWARGgjVfX3ZUeJiJ4+ixxxa7k="');
  process.exit(1);
}

/**
 * Simple JWT generator without external dependencies
 */
function generateJWT(payload, secret, expiresInYears = 10) {
  // Header
  const header = {
    alg: 'HS256',
    typ: 'JWT'
  };

  // Calculate expiration (10 years from now)
  const now = Math.floor(Date.now() / 1000);
  const exp = now + (expiresInYears * 365 * 24 * 60 * 60);

  // Payload
  const claims = {
    ...payload,
    iat: now,
    exp: exp
  };

  // Encode header and payload
  const base64UrlEncode = (obj) => {
    return Buffer.from(JSON.stringify(obj))
      .toString('base64')
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  };

  const encodedHeader = base64UrlEncode(header);
  const encodedPayload = base64UrlEncode(claims);

  // Create signature
  const signatureInput = `${encodedHeader}.${encodedPayload}`;
  const signature = crypto
    .createHmac('sha256', secret)
    .update(signatureInput)
    .digest('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');

  return `${encodedHeader}.${encodedPayload}.${signature}`;
}

// Generate keys
console.log('');
console.log('═══════════════════════════════════════════════════════════');
console.log('  Supabase JWT Keys');
console.log('═══════════════════════════════════════════════════════════');
console.log('');

const anonKey = generateJWT({
  role: 'anon',
  iss: 'supabase'
}, JWT_SECRET);

const serviceRoleKey = generateJWT({
  role: 'service_role',
  iss: 'supabase'
}, JWT_SECRET);

console.log('SUPABASE_ANON_KEY (safe to expose in frontend):');
console.log(anonKey);
console.log('');
console.log('SUPABASE_SERVICE_ROLE_KEY (SECRET - backend only):');
console.log(serviceRoleKey);
console.log('');
console.log('═══════════════════════════════════════════════════════════');
console.log('');
console.log('Copy these values to your .env file:');
console.log('');
console.log(`SUPABASE_ANON_KEY=${anonKey}`);
console.log(`SUPABASE_SERVICE_ROLE_KEY=${serviceRoleKey}`);
console.log('');
