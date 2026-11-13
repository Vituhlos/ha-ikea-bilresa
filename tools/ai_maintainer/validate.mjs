// Deliberately small JSON Schema subset used by the checked-in schemas. Unknown
// keywords fail closed so a schema extension cannot silently bypass validation.
const supported = new Set(['$schema', 'title', 'type', 'properties', 'required',
  'additionalProperties', 'items', 'maxItems', 'maxLength', 'minimum', 'pattern', 'enum', 'const', 'anyOf']);

export function validate(schema, value) {
  for (const key of Object.keys(schema)) if (!supported.has(key)) throw new Error('Unsupported schema keyword');
  if (schema.anyOf) {
    if (!schema.anyOf.some(s => { try { validate(s, value); return true; } catch { return false; } })) throw new Error('Invalid alternative');
  }
  if ('const' in schema && value !== schema.const) throw new Error('Invalid constant');
  if (schema.enum && !schema.enum.includes(value)) throw new Error('Invalid enum');
  if (schema.type) {
    const matches = { object: value !== null && typeof value === 'object' && !Array.isArray(value),
      array: Array.isArray(value), string: typeof value === 'string', boolean: typeof value === 'boolean',
      integer: Number.isSafeInteger(value), null: value === null };
    if (!matches[schema.type]) throw new Error('Invalid type');
  }
  if (typeof value === 'string') {
    if (schema.maxLength !== undefined && value.length > schema.maxLength) throw new Error('String limit');
    if (schema.pattern && !new RegExp(schema.pattern).test(value)) throw new Error('Invalid pattern');
  }
  if (typeof value === 'number' && schema.minimum !== undefined && value < schema.minimum) throw new Error('Invalid minimum');
  if (Array.isArray(value)) {
    if (schema.maxItems !== undefined && value.length > schema.maxItems) throw new Error('Array limit');
    if (schema.items) for (const item of value) validate(schema.items, item);
  } else if (value !== null && typeof value === 'object') {
    for (const key of schema.required ?? []) if (!Object.hasOwn(value, key)) throw new Error('Missing property');
    for (const key of Object.keys(value)) {
      if (Object.hasOwn(schema.properties ?? {}, key)) validate(schema.properties[key], value[key]);
      else if (schema.additionalProperties === false) throw new Error('Unexpected property');
    }
  }
  return value;
}

export function validateReport(schema, report) {
  validate(schema, report);
  if (report.complete !== (report.missing.length === 0)) throw new Error('Inconsistent completeness');
  if (report.item.kind === 'pull_request' && (!report.refs.prBase || !report.refs.prHead)) throw new Error('Missing PR refs');
  for (const file of [...report.evidence, ...report.absences]) {
    if (report.refs[file.role]?.sha !== file.revision) throw new Error('Evidence revision mismatch');
  }
  for (const check of report.validation.checks) {
    if (report.refs.prHead?.sha !== check.revision) throw new Error('Check revision mismatch');
  }
  return report;
}
