#!/usr/bin/env node
/**
 * Patch script for frappe-gantt to fix Month view bar positioning
 *
 * The issue: In Month view, bars are misaligned because the library
 * uses a fixed 30-day month assumption for position calculations,
 * but months have varying days (28-31).
 *
 * This script enables the commented-out Month view fix in bar.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const barJsPath = path.join(__dirname, '../node_modules/frappe-gantt/src/bar.js');

// Check if file exists
if (!fs.existsSync(barJsPath)) {
    console.log('frappe-gantt not installed yet, skipping patch');
    process.exit(0);
}

let content = fs.readFileSync(barJsPath, 'utf8');

// Check if already patched
if (content.includes('// PATCHED: Month view fix enabled')) {
    console.log('frappe-gantt already patched');
    process.exit(0);
}

// The fix: uncomment the Month view positioning code in compute_x()
// Original commented code is at lines ~586-604
const commentedCode = `        // if (this.gantt.view_is('Month')) {
        //     const diffDaysBasedOn30DayMonths =
        //         date_utils.diff(task_start, gantt_start, 'month') * 30;
        //     const dayInMonth = Math.min(
        //         29,
        //         date_utils.format(
        //             task_start,
        //             'DD',
        //             this.gantt.options.language,
        //         ),
        //     );
        //     const diff = diffDaysBasedOn30DayMonths + dayInMonth;

        //     x = (diff * column_width) / 30;
        // }`;

const fixedCode = `        // PATCHED: Month view fix enabled
        if (this.gantt.view_is('Month')) {
            const diffDaysBasedOn30DayMonths =
                date_utils.diff(task_start, gantt_start, 'month') * 30;
            const dayInMonth = Math.min(
                29,
                parseInt(date_utils.format(
                    task_start,
                    'DD',
                    this.gantt.options.language,
                ), 10),
            );
            const diff = diffDaysBasedOn30DayMonths + dayInMonth;

            x = (diff * column_width) / 30;
        }`;

if (content.includes(commentedCode)) {
    content = content.replace(commentedCode, fixedCode);
    fs.writeFileSync(barJsPath, content);
    console.log('Successfully patched frappe-gantt for Month view fix');
} else {
    console.log('Warning: Could not find expected code to patch in bar.js');
    console.log('The library may have been updated. Manual patching may be required.');
    process.exit(1);
}
