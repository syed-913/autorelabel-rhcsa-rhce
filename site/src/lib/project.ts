import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {parse} from 'smol-toml';

const manifest=parse(readFileSync(resolve(process.cwd(),'../pyproject.toml'),'utf8')) as {project?:{version?:unknown}};
const packageVersion=manifest.project?.version;
if(typeof packageVersion!=='string'||!packageVersion.trim())throw new Error('Missing project.version in pyproject.toml');
export const version=packageVersion;
