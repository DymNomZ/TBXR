import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dataDiagramsDir = path.resolve(__dirname, '../documentation/data diagrams');
const pngsDir = path.join(dataDiagramsDir, 'pngs');

if (!fs.existsSync(pngsDir)) {
    fs.mkdirSync(pngsDir, { recursive: true });
}

const files = fs.readdirSync(dataDiagramsDir).filter(f => f.endsWith('.md'));

console.log(`Found ${files.length} markdown diagram files.`);

for (const file of files) {
    const baseName = path.basename(file, '.md');
    const inputPath = path.join(dataDiagramsDir, file);
    const targetPng = path.join(pngsDir, `${baseName}.png`);
    const tempOutput = path.join(pngsDir, `${baseName}_tmp.png`);

    console.log(`Rendering ${file}...`);
    try {
        execSync(`npx mmdc -i "${inputPath}" -o "${tempOutput}" -b white -s 2`, {
            cwd: __dirname,
            stdio: 'pipe'
        });

        // mmdc names it tempOutput-1.png for markdown files
        const generatedFile = path.join(pngsDir, `${baseName}_tmp-1.png`);
        if (fs.existsSync(generatedFile)) {
            if (fs.existsSync(targetPng)) {
                fs.unlinkSync(targetPng);
            }
            fs.renameSync(generatedFile, targetPng);
            console.log(`Successfully generated ${baseName}.png`);
        } else if (fs.existsSync(tempOutput)) {
            if (fs.existsSync(targetPng)) {
                fs.unlinkSync(targetPng);
            }
            fs.renameSync(tempOutput, targetPng);
            console.log(`Successfully generated ${baseName}.png`);
        } else {
            console.error(`Warning: Output file not found for ${file}`);
        }
    } catch (err) {
        console.error(`Error rendering ${file}:`, err.message);
    }
}

// Remove the initial test file 1.1_Data Diagram-1.png if it exists
const testFile = path.join(pngsDir, '1.1_Data Diagram-1.png');
if (fs.existsSync(testFile)) {
    fs.unlinkSync(testFile);
}

console.log('All diagrams generated successfully.');
